# do semantic search on all users (store embedding in storage)
# choose what columns to show
# load in a particular user and get post stats
# - number of posts in each status
# join with business table to get business name
# aggregates and plotting
# filter named,anonymous,all
from datetime import datetime
import numpy as np
import pandas as pd
from pandas import json_normalize
import streamlit as st
from utils import db

st.set_page_config(layout='wide', page_title="Users", page_icon="💁‍♂️")

users = db.list_users_joined_businesses()
flattened_businesses = json_normalize(users)
df = pd.DataFrame(flattened_businesses)
df = df[~(df['email'].str.startswith('markytest') | df['email'].str.startswith('betalingtester'))]
df.replace('__GSI_NULL', np.nan, inplace=True)
df['trial_details.cancelled'] = (~df['trial_details.cancelled_at'].isna())
df['trial_details.subscribed'] = (~df['trial_details.subscribed_at'].isna())
df['trial_details.failed_payment'] = (~df['trial_details.payment_last_failed_at'].isna())
df['trial_details.hit_stripe'] = (~df['trial_details.customer_id'].isna())
df['trial_details.trialed'] = (~df['trial_details.started_trial_at'].isna())
df['created_at'] = pd.to_datetime(df['created_at'])
df['created_at_timestamp'] = df['created_at_timestamp'].astype(int)
df['signedup'] = df['email'].notna()

with st.sidebar:
    # select columns to show
    cols_selected = st.multiselect("Columns", df.columns.tolist(), default=df.columns.tolist())
    db.save_storage('USER_COLUMNS_SELECTED', cols_selected)

from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
import pandas as pd
import streamlit as st


def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns

    Args:
        df (pd.DataFrame): Original dataframe

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    modify = st.checkbox("Add filters")

    if not modify:
        return df

    df = df.copy()

    # Try to convert datetimes into a standard format (datetime, no timezone)
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect("Filter dataframe on", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            # Treat columns with < 10 unique values as categorical
            # is boolean type
            if df[column].dtype == bool:
                user_bool_input = right.checkbox(f"Values for {column}", value=True)
                df = df[df[column] == user_bool_input]
            elif is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    min_value=_min,
                    max_value=_max,
                    value=(_min, _max),
                    step=step,
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                )
                if user_text_input:
                    df = df[df[column].astype(str).str.contains(user_text_input)]

    return df


df = filter_dataframe(df)
st.write(f"Found {df.shape[0]} users matching filters")
cols_selected = db.get_storage('USER_COLUMNS_SELECTED')
cols_selected.sort()
st.dataframe(df[cols_selected], use_container_width=True)


import plotly.graph_objects as go

st.markdown('---')
st.header('Stats (Last 24 hours)')
import streamlit as st

def create_card(header, value, subheader=None):
    with st.container():
        st.header(header)
        if subheader:
            st.subheader(subheader)
        st.write(value)


last_24 = df[df['created_at'] > datetime.now() - pd.Timedelta(days=1)]
demoed_last_24 = last_24['signedup'].count()
signedup_last_24 = last_24['signedup'].sum()
trialed_last_24 = last_24['trial_details.trialed'].sum()
hit_paywall_last_24 = last_24['trial_details.hit_paywall'].sum()
subscribed_last_24 = last_24['trial_details.subscribed'].sum()

cols = st.columns(4)
with cols[0]:
    create_card("Demoed", demoed_last_24)
with cols[1]:
    create_card("Signed Up", signedup_last_24)
with cols[2]:
    create_card("Trialed", trialed_last_24)
with cols[3]:
    create_card("Subscribed", subscribed_last_24)

import plotly.express as px
# data = dict(
#     number=[demoed_last_24, signedup_last_24, hit_paywall_last_24, trialed_last_24],
#     stage=["Demoed", "Signed Up", "Paywall", "Trialed"])
# fig = px.funnel(data, x='number', y='stage')
# st.plotly_chart(fig)

from plotly import graph_objects as go

fig = go.Figure(go.Funnel(
    y = ["Demoed", "Signed Up", "Paywall", "Trialed"],
    x = [demoed_last_24, signedup_last_24, hit_paywall_last_24, trialed_last_24],
    textposition = "inside",
    textinfo = "value+percent initial",
    ))
st.plotly_chart(fig)

st.markdown('---')
st.header('Charts')
col1, col2 = st.columns([1, 5], gap='large')
ncols = col1.slider('Columns', 1, 4, 2)
col_counter = 0

agg_window_display_names = {'D': "Daily", 'W': "Weekly", 'M': "Monthly"}
group_time = col2.selectbox("Aggregation Window", list(agg_window_display_names.keys()), format_func=lambda x: agg_window_display_names[x])

cols = st.columns(ncols)

with cols[col_counter % ncols]:
    records = df.resample(group_time, on='created_at')['created_at'].size()
    signups = df.resample(group_time, on='created_at')['signedup'].sum()
    records = records.iloc[:-1]
    signups = signups.iloc[:-1]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=records.index, y=records.values, name='Records Created'))
    fig.add_trace(go.Scatter(x=signups.index, y=signups.values, name='User Signups'))
    fig.update_layout(title='Daily Records and User Signups')
    st.plotly_chart(fig, use_container_width=True)

col_counter += 1
with cols[col_counter % ncols]:
    # show the ratio
    ratio = signups / records
    fig = go.Figure(data=go.Scatter(x=ratio.index, y=ratio.values))
    fig.update_layout(title='Omnibox -> Signup')
    fig.update_yaxes(range=[0, 1])
    st.plotly_chart(fig, use_container_width=True)

col_counter += 1
with cols[col_counter % ncols]:
    # plot conversion rate of people that hit paywall and then trialed
    df_after_nov19 = df.loc[df['created_at'] > datetime(2023, 11, 19)]
    hit_paywall = df_after_nov19.resample(group_time, on='created_at')['trial_details.hit_paywall'].sum()
    started_trial = df_after_nov19.resample(group_time, on='created_at')['trial_details.trialed'].sum()
    conversion_rate = started_trial / hit_paywall
    conversion_rate = conversion_rate.iloc[:-1]
    fig = go.Figure(data=go.Scatter(x=conversion_rate.index, y=conversion_rate.values))
    fig.update_layout(title='Paywall -> Trial Rate')
    fig.update_yaxes(range=[0, 0.5])
    st.plotly_chart(fig, use_container_width=True)

col_counter += 1
with cols[col_counter % ncols]:
    # plot conversion rate of people that signed up account and then trialed
    signed_up = df.resample(group_time, on='created_at')['signedup'].sum()
    started_trial = df.resample(group_time, on='created_at')['trial_details.trialed'].sum()
    conversion_rate = started_trial / signed_up
    conversion_rate = conversion_rate.iloc[:-1]
    fig = go.Figure(data=go.Scatter(x=conversion_rate.index, y=conversion_rate.values))
    fig.update_layout(title='Signup -> Trial Rate')
    fig.update_yaxes(range=[0, 0.5])
    st.plotly_chart(fig, use_container_width=True)

col_counter += 1
with cols[col_counter % ncols]:
    # plot trial -> conversion rate
    df_after_oct8 = df.loc[df['created_at'] > datetime(2023, 10, 8)]
    started_trial = df_after_oct8.resample(group_time, on='created_at')['trial_details.trialed'].sum()
    subscribed = df_after_oct8.resample(group_time, on='created_at')['trial_details.subscribed'].sum()
    conversion_rate = subscribed / started_trial
    conversion_rate = conversion_rate.iloc[:-1]
    fig = go.Figure(data=go.Scatter(x=conversion_rate.index, y=conversion_rate.values))
    fig.update_layout(title='Trial -> Subscribe Rate')
    st.plotly_chart(fig, use_container_width=True)

col_counter += 1
with cols[col_counter % ncols]:
    # plot agencies
    agency_signups = df.resample(group_time, on='created_at')['is_agency'].sum()
    agency_signups = agency_signups.iloc[:-1]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=agency_signups.index, y=agency_signups.values))
    fig.update_layout(title='Agency Signups')
    st.plotly_chart(fig, use_container_width=True)

col_counter += 1
with cols[col_counter % ncols]:
    # number of subscribers
    subscribed = df_after_oct8.resample(group_time, on='created_at')['trial_details.subscribed'].sum()
    subscribed = subscribed.iloc[:-1]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=subscribed.index, y=subscribed.values))
    fig.update_layout(title='Subscribed')
    st.plotly_chart(fig, use_container_width=True)
