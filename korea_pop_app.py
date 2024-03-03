#######################
# 라이브러리 불러오기
import streamlit as st
import pandas as pd
import geopandas as gpd
import altair as alt
import plotly.express as px

#######################
# 페이지 설정
st.set_page_config(
    page_title="대한민국 인구 변화 대시보드",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded")

alt.themes.enable("dark")


#######################
# 데이터 불러오기
df = pd.read_csv('data/201412_202312_korea_population_year.csv', encoding='cp949') # cp949 : 한글 인코딩
korea_geojson = gpd.read_file('data/SIDO_MAP_2022_geoJSON.json') # geopandas의 read_file 함수로 데이터 불러오기

#######################
# 데이터 전처리
df.bfill(inplace=True) # NaN값을 아래의 값으로 채움
df.drop(11, inplace=True) # 11번째 행(강원자치도) 삭제
df.drop(0, inplace=True) # 0번째 행(전국) 삭제
df.reset_index(drop=True, inplace=True) # 인덱스 재설정

# 행정구역을 기준으로 데이터를 쪼개서 새로운 열로 만들기
# expand=True : 쪼개진 데이터를 새로운 열로 만들어줌
df[['city', 'code']] = df['행정구역'].str.split('(', expand=True) 
df['code'] = df['code'].str.strip(')').str.replace('00000000', '')  # 코드에 있는 괄호 제거하고 00000000을 공백으로 변경
df.drop('행정구역', axis=1, inplace=True) # 행정구역 열 삭제

df = df.melt(
    id_vars=['city', 'code'], 
    var_name='property', 
    value_name='population',
)

df[['year', 'category']] = df['property'].str.split('년_', expand=True) # 속성을 연도와 구분으로 나누기
df.drop('property', axis=1, inplace=True) # 속성 열 삭제

df['population'] = df['population'].str.replace(',', '').astype('int') # 인구수를 쉼표를 삭제한 후 정수로 변환 (문자열 -> 정수)
df['year'] = df['year'].astype('int') # 연도를 정수로 변환 (문자열 -> 정수)

df = df[['city', 'code', 'year', 'category', 'population']] # 열 순서 변경

#######################
# 사이드바 설정

with st.sidebar:
    st.title('🏂 대한민국 인구 대시보드')
    
    year_list = list(df.year.unique())[::-1]  # 연도 리스트를 내림차순으로 정렬
    category_list = list(df.category.unique())  # 카테고리 리스트
    
    selected_year = st.selectbox('연도 선택', year_list) # selectbox에서 연도 선택
    selected_category = st.selectbox('카테고리 선택', category_list) # selectbox에서 카테고리 선택

    df_selected_year = df.query('year == @selected_year & category == @selected_category') # 선택한 연도와 카테고리에 해당하는 데이터만 가져오기
    df_selected_year_sorted = df_selected_year.sort_values(by="population", ascending=False) # 선택한 연도와 카테고리에 해당하는 데이터를 인구수를 기준으로 내림차순 정렬

    color_theme_list = ['blues', 'cividis', 'greens', 'inferno', 'magma', 'plasma', 'reds', 'rainbow', 'turbo', 'viridis']
    selected_color_theme = st.selectbox('컬러 테마 선택', color_theme_list)


#######################
# 그래프 함수

# Heatmap 그래프
def make_heatmap(input_df, input_y, input_x, input_color, input_color_theme):
    heatmap = alt.Chart(input_df).mark_rect().encode(
            y=alt.Y(f'{input_y}:O', axis=alt.Axis(title="연도", titleFontSize=18, titlePadding=15, titleFontWeight=900, labelAngle=0)),
            x=alt.X(f'{input_x}:O', axis=alt.Axis(title="", titleFontSize=18, titlePadding=15, titleFontWeight=900)),
            color=alt.Color(f'max({input_color}):Q',
                             legend=None,
                             scale=alt.Scale(scheme=input_color_theme)),
            stroke=alt.value('black'),
            strokeWidth=alt.value(0.25),
        ).properties(width=900
        ).configure_axis(
        labelFontSize=12,
        titleFontSize=12
        ) 
    # height=300
    return heatmap

# Choropleth map
def make_choropleth(input_df, input_gj, input_column, input_color_theme):
    choropleth = px.choropleth_mapbox(input_df,
                               geojson=input_gj,
                               locations='code', 
                               featureidkey='properties.CTPRVN_CD',
                               mapbox_style='carto-darkmatter',
                               zoom=5, 
                               center = {"lat": 35.9, "lon": 126.98},
                               color=input_column, 
                               color_continuous_scale=input_color_theme,
                               range_color=(0, max(input_df.population)),
                               labels={'population':'인구수', 'code':'시도코드', 'city':'시도명'},
                               hover_data=['city', 'population']
                              )
    choropleth.update_geos(fitbounds="locations", visible=False)
    choropleth.update_layout(
        template='plotly_dark',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        margin=dict(l=0, r=0, t=0, b=0),
        height=350
    )
    return choropleth


# 도넛 차트
def make_donut(input_response, input_text, input_color):
  if input_color == 'blue':
      chart_color = ['#29b5e8', '#155F7A']
  if input_color == 'green':
      chart_color = ['#27AE60', '#12783D']
  if input_color == 'orange':
      chart_color = ['#F39C12', '#875A12']
  if input_color == 'red':
      chart_color = ['#E74C3C', '#781F16']
    
  source = pd.DataFrame({
      "Topic": ['', input_text],
      "% value": [100-input_response, input_response]
  })
  source_bg = pd.DataFrame({
      "Topic": ['', input_text],
      "% value": [100, 0]
  })
    
  plot = alt.Chart(source).mark_arc(innerRadius=45, cornerRadius=25).encode(
      theta="% value",
      color= alt.Color("Topic:N",
                      scale=alt.Scale(
                          #domain=['A', 'B'],
                          domain=[input_text, ''],
                          # range=['#29b5e8', '#155F7A']),  # 31333F
                          range=chart_color),
                      legend=None),
  ).properties(width=130, height=130)
    
  text = plot.mark_text(align='center', color="#29b5e8", font="Lato", fontSize=32, fontWeight=700, fontStyle="italic").encode(text=alt.value(f'{input_response} %'))
  plot_bg = alt.Chart(source_bg).mark_arc(innerRadius=45, cornerRadius=20).encode(
      theta="% value",
      color= alt.Color("Topic:N",
                      scale=alt.Scale(
                          # domain=['A', 'B'],
                          domain=[input_text, ''],
                          range=chart_color),  # 31333F
                      legend=None),
  ).properties(width=130, height=130)
  return plot_bg + plot + text # 백그라운드, 차트, 텍스트를 합쳐서 그래프 생성

# Convert population to text 
def format_number(num):
    if num > 1000000:
        if not num % 1000000:
            return f'{num // 1000000} M'
        return f'{round(num / 1000000, 1)} M'
    return f'{num // 1000} K'

# Calculation year-over-year population migrations
def calculate_population_difference(input_df, input_year, input_category):
  selected_year_data = input_df.query('year == @input_year & category == @input_category').reset_index()
  previous_year_data = input_df.query('year == @input_year-1 & category == @input_category').reset_index()
  selected_year_data['population_difference'] = selected_year_data['population'].sub(previous_year_data['population'], fill_value=0)
  selected_year_data['population_difference_abs'] = abs(selected_year_data['population_difference'])
  return pd.concat([
    selected_year_data['city'], 
    selected_year_data['code'], 
    selected_year_data['population'], 
    selected_year_data['population_difference'], 
    selected_year_data['population_difference_abs']
    ], axis=1).sort_values(by='population_difference', ascending=False)

#######################
# 대시보드 레이아웃
col = st.columns((1.5, 4.5, 2), gap='medium')

with col[0]: # 왼쪽
    st.markdown('#### 증가/감소')

    df_population_difference_sorted = calculate_population_difference(df, selected_year, selected_category)

    if selected_year > 2014:
        first_state_name = df_population_difference_sorted.city.iloc[0]
        first_state_population = format_number(df_population_difference_sorted.population.iloc[0])
        first_state_delta = format_number(df_population_difference_sorted.population_difference.iloc[0])
    else:
        first_state_name = '-'
        first_state_population = '-'
        first_state_delta = ''
    st.metric(label=first_state_name, value=first_state_population, delta=first_state_delta)

    if selected_year > 2014:
        last_state_name = df_population_difference_sorted.city.iloc[-1]
        last_state_population = format_number(df_population_difference_sorted.population.iloc[-1])   
        last_state_delta = format_number(df_population_difference_sorted.population_difference.iloc[-1])   
    else:
        last_state_name = '-'
        last_state_population = '-'
        last_state_delta = ''
    st.metric(label=last_state_name, value=last_state_population, delta=last_state_delta)

    
    st.markdown('#### 변동 시도 비율')

    if selected_year > 2014:
        # Filter states with population difference > 5000
        # df_greater_50000 = df_population_difference_sorted[df_population_difference_sorted.population_difference_absolute > 50000]
        df_greater_5000 = df_population_difference_sorted[df_population_difference_sorted.population_difference > 5000]
        df_less_5000 = df_population_difference_sorted[df_population_difference_sorted.population_difference < -5000]
        
        # % of States with population difference > 5000
        states_migration_greater = round((len(df_greater_5000)/df_population_difference_sorted.city.nunique())*100)
        states_migration_less = round((len(df_less_5000)/df_population_difference_sorted.city.nunique())*100)
        donut_chart_greater = make_donut(states_migration_greater, '전입', 'green')
        donut_chart_less = make_donut(states_migration_less, '전출', 'red')
    else:
        states_migration_greater = 0
        states_migration_less = 0
        donut_chart_greater = make_donut(states_migration_greater, '전입', 'green')
        donut_chart_less = make_donut(states_migration_less, '전출', 'red')

    migrations_col = st.columns((0.2, 1, 0.2))
    with migrations_col[1]:
        st.write('증가')
        st.altair_chart(donut_chart_greater)
        st.write('감소')
        st.altair_chart(donut_chart_less)

with col[1]:
    st.markdown('#### ' + str(selected_year) + '년 ' + str(selected_category))
    
    choropleth = make_choropleth(df_selected_year, korea_geojson, 'population', selected_color_theme)
    st.plotly_chart(choropleth, use_container_width=True)
    
    heatmap = make_heatmap(df, 'year', 'city', 'population', selected_color_theme)
    st.altair_chart(heatmap, use_container_width=True)
    

with col[2]:
    st.markdown('#### 시도별 ' + str(selected_category))

    st.dataframe(df_selected_year_sorted,
                 column_order=("city", "population"),
                 hide_index=True,
                 width=500,
                 column_config={
                    "city": st.column_config.TextColumn(
                        "시도명",
                    ),
                    "population": st.column_config.ProgressColumn(
                        str(selected_category),
                        format="%f",
                        min_value=0,
                        max_value=max(df_selected_year_sorted.population),
                     )}
                 )
    
    with st.expander('정보', expanded=True):
        st.write('''
            - 데이터: [행정안전부 주민등록 인구통계](https://jumin.mois.go.kr/).
            - :orange[**증가/감소**]: 선택 연도에서 가장 많이 증가/감소한 시도 
            - :orange[**변동 시도 비율**]: 선택 연도에서 인구가 5000명 이상 증가/감소한 시도의 비율
            ''')
