#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May 22 20:42:24 2021

@author: songyang
"""

import base64
import io
import re
# Ignore warnings
import warnings
from datetime import datetime, time
from decimal import Decimal

import pandas as pd
import plotly.graph_objects as go
from PIL import Image
from plotly.subplots import make_subplots

# 额外加上对HEIC的支持
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    # 如果没装pillow_heif，就会无法打开heic
    # 可以抛异常，也可以仅做提醒
    print("Warning: pillow_heif not installed. iPhone HEIC images may fail to open.")

# ======================== AWS Related ====================================
import boto3
from boto3.dynamodb.conditions import Key

# ======================== LLM Import ====================================
from typing import List
from pydantic import BaseModel, Field

warnings.filterwarnings("ignore")


# %% ===========================================================================
# # Class Defined
# =============================================================================


header_name_mapping = {'food_item': 'Food Item', 'portion': 'Portion', 'calories': 'Calories',
                       'protein_g': 'Protein(g)', 'fat_g': 'Fat(g)',
                       'saturated_fat_g': 'Sat. Fat(g)', 'carbs_g': 'Carbs. (g)',
                       'meal_date': 'Meal Date', 'meal_type': 'Meal Type'
                       }


# %% ===========================================================================
# # AWS Write or Read
# =============================================================================
def convert_floats(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats(i) for i in obj]
    return obj


# 工具函数：递归把 DynamoDB 的 Decimal 转成 float
def convert_decimals(obj):
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    if isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj) if obj % 1 else int(obj)
    return obj


def write_record_to_dynamodb(table_name, user_id, new_records_df):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    df_ = new_records_df.copy()
    timestamp = datetime.now().strftime('%H%M%S')
    df_['user_id'] = user_id
    df_['timestamp'] = df_.apply(lambda x: f"{x['meal_date']}|{timestamp}|{x['food_item']}", axis=1)

    # Register the creation time before upload
    df_['create_timestamp'] = datetime.now().isoformat()

    with table.batch_writer() as batch:
        for item in df_.to_dict('records'):
            batch.put_item(Item=convert_floats(item))


# 主函数：输入表名、用户 ID、时间范围，返回 DataFrame
def query_user_records_to_dataframe(table_name, user_id, start_datetime, end_datetime):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    # 时间范围字符串，前缀匹配用
    start_prefix = start_datetime.strftime('%Y-%m-%d')+'|'
    end_prefix = end_datetime.strftime('%Y-%m-%d')+'|~'

    response = table.query(
        KeyConditionExpression=Key('user_id').eq(user_id) &
                               Key('timestamp').between(start_prefix, end_prefix)  # 加 '~' 确保包含所有食物
    )

    items = response['Items']

    # 分页处理：如果有多页结果
    while 'LastEvaluatedKey' in response:
        response = table.query(
            KeyConditionExpression=Key('user_id').eq(user_id) &
                                   Key('timestamp').between(start_prefix, end_prefix + '|zzz'),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response['Items'])

    # 处理 Decimal 类型
    items = convert_decimals(items)

    # 转成 DataFrame
    df = pd.DataFrame(items)

    if not df.empty:
        # 拆分 timestamp 成两列：date_time 和 food_item
        df['meal_date'] = df['timestamp'].apply(lambda x: x.split('|')[0])

        # 排序方便分析
        df = df.sort_values('meal_date')

    return df


# %% ===========================================================================
# # I/O Related Functions
# =============================================================================
# convert input base64 image to image which pytorch can identify
def base64_to_image(base64_str):
    match = re.match(r'^data:image/(?P<fmt>\w+);base64,', base64_str)
    if not match:
        raise ValueError("Unsupported base64 image format (missing data:image/xxx;base64, prefix)")

    img_format = match.group("fmt").upper()
    base64_data = re.sub('^data:image/.+;base64,', '', base64_str)
    byte_data = base64.b64decode(base64_data)
    image_data = io.BytesIO(byte_data)
    img = Image.open(image_data)

    return img, img_format


def image_to_base64(img, img_format="JPEG"):
    buffer = io.BytesIO()

    # Pillow uses "JPEG", not "JPG"
    if img_format == "JPG" or img_format.lower() == "heic":
        img_format = "JPEG"

    img.save(buffer, format=img_format)
    base64_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/{img_format.lower()};base64,{base64_str}", base64_str


def process_upload_img(contents: str, b_crop_to_512: bool = False):
    img, img_format = base64_to_image(contents)

    if b_crop_to_512:
        # Crop to center square
        width, height = img.size
        min_dim = min(width, height)
        left = (width - min_dim) // 2
        top = (height - min_dim) // 2
        right = left + min_dim
        bottom = top + min_dim
        img_cropped = img.crop((left, top, right, bottom))
        img_resized = img_cropped.resize((512, 512), Image.LANCZOS)
    else:
        # Resize with aspect ratio preserved, long side = 512
        width, height = img.size
        if width >= height:
            new_width = 512
            new_height = int(height * 512 / width)
        else:
            new_height = 512
            new_width = int(width * 512 / height)
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)

    if img_format.lower() == "heic":
        img_format = "JPEG"

    base64_resized_str, raw_base64_bytes = image_to_base64(img_resized, img_format)

    return img_resized, base64_resized_str, raw_base64_bytes


def parse_response_to_dataframe(response):
    df = pd.DataFrame([item.model_dump() for item in response.items])
    total_row = pd.DataFrame([response.total.model_dump()])
    df_with_total = pd.concat([df, total_row], ignore_index=True)

    return df_with_total


# %% ===========================================================================
# # Business Related Functions
# =============================================================================
def get_meal_time(current_datetime=datetime.now()):
    current_time = current_datetime.time()
    # Define meal times
    breakfast = (time(5, 0), time(10, 0))
    lunch = (time(11, 0), time(14, 0))
    dinner = (time(18, 0), time(21, 0))

    # Check time range
    if breakfast[0] <= current_time <= breakfast[1]:
        return "Breakfast"
    elif lunch[0] <= current_time <= lunch[1]:
        return "Lunch"
    elif dinner[0] <= current_time <= dinner[1]:
        return "Dinner"
    else:
        return "Snack"


def get_latest_creation_records(df_raw):
    df_latest = df_raw.copy()
    df_latest['latest_rank'] = df_latest.groupby(['meal_date', 'meal_type', 'food_item'],
                                                 as_index=False)['create_timestamp'].transform(
        lambda x: x.rank(ascending=False, method='dense'))
    df_latest = df_latest[df_latest['latest_rank'] == 1].copy()
    df_latest.drop(columns='latest_rank', inplace=True)
    return df_latest

NUM_COLS = ["calorie", "fat_g", "protein_g", "carb_g"]
def get_plot_today_records_fig(plot_df):
    plot_df = plot_df[plot_df['food_item'] != 'Total Meal'].reset_index(drop=True).copy()

    # Convert to number
    for col in NUM_COLS:
        if col in plot_df.columns:
            plot_df[col] = plot_df[col].astype(float)

    df_grp = plot_df.groupby('meal_date', as_index=False)[
        ['calories', 'carbs_g', 'protein_g', 'fat_g', 'saturated_fat_g']].sum()
    df_grp['unsaturated_fat_g'] = df_grp['fat_g'] - df_grp['saturated_fat_g']

    # Create subplots
    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[1, 3],
        subplot_titles=['Calories', 'Nutrition']
    )

    # Left: Calories
    fig.add_trace(
        go.Bar(x=['calories'], y=df_grp['calories'], name='Calories', marker_color='steelblue', showlegend=False),
        row=1, col=1
    )

    # Right: Nutrition
    nutrients = {
        'carbs_g': 'orange',
        'protein_g': 'green',
        'saturated_fat_g': 'crimson',
        'unsaturated_fat_g': 'lightsalmon'
    }

    for nutrient, color in nutrients.items():
        fig.add_trace(
            go.Bar(x=['fat_g'] if 'fat' in nutrient else [nutrient],
                   y=df_grp[nutrient], name=nutrient.replace('_g', '').replace('_', ' ').title(), marker_color=color),
            row=1, col=2
        )

    # Layout settings
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(size=20)  # Or any size you want
    fig.update_layout(
        barmode='stack',
        title_font_size=20,
        legend=dict(font=dict(size=14)),
        template='plotly_white')
    fig.update_yaxes(title_text='Energy (Kcal)', row=1, col=1, title_font_size=17)
    fig.update_yaxes(title_text='Nutrition (g)', row=1, col=2, title_font_size=17)
    fig.update_xaxes(title_font_size=20, tickfont=dict(size=15))
    return fig


def get_plot_range_records_fig(plot_df, metric):
    # plot_df = df_7days_latest.copy()
    # metric = 'calories'
    plot_df = plot_df[plot_df['food_item'] != 'Total Meal'].reset_index(drop=True).copy()
    # Convert to number
    for col in NUM_COLS:
        if col in plot_df.columns:
            plot_df[col] = plot_df[col].astype(float)

    y_title = 'Energy (Kcal)' if metric == 'calories' else 'Nutrition (g)'
    metric_title_name = metric.replace('_g', '').title()

    df_grp = plot_df.groupby('meal_date', as_index=False)[
        ['calories', 'carbs_g', 'protein_g', 'fat_g', 'saturated_fat_g']].sum()
    df_grp['unsaturated_fat_g'] = df_grp['fat_g'] - df_grp['saturated_fat_g']
    df_grp['meal_date'] = df_grp['meal_date'].astype(str)
    df_grp.sort_values('meal_date', ascending=True, inplace=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_grp['meal_date'].values, y=df_grp[metric].values, name=metric_title_name))
    fig.update_xaxes(tickformat="%Y-%m-%d")
    fig.update_layout(
        title_text=metric_title_name,
        title_font_size=20,
        legend=dict(font=dict(size=14)),
        template='plotly_white')
    fig.update_yaxes(title_text=y_title, title_font_size=17)
    fig.update_xaxes(title_font_size=20, tickfont=dict(size=15))
    return fig
