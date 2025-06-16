import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Dashboard Monitoring", layout="wide")

@st.cache_data
def load_data():
    return pd.read_parquet("courier_insentif_new.parquet")

df = load_data()

@st.cache_data
def load_data_sla():
    return pd.read_parquet("pickup_perfomance1.parquet")

df_sla = load_data_sla()

# UI Header
st.title("📦 Dashboard Monitoring Kurir dan Gerai")

# Filter tanggal
df['PICKUP_DATE_TIME'] = pd.to_datetime(df['PICKUP_DATE_TIME'])
min_date = df['PICKUP_DATE_TIME'].min().date()
max_date = df['PICKUP_DATE_TIME'].max().date()

date_range = st.date_input(
    "📅 Pilih Rentang Tanggal Pickup",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# 📊 FILTER TOP N GERAI
# -----------------------------

# pilih 1 tanggal
if len(date_range) == 2:
    start_date, end_date = date_range
elif len(date_range) == 1:
    start_date = end_date = date_range[0]
else:
    st.warning("Silakan pilih minimal satu tanggal terlebih dahulu.")
    st.stop()

# Filter
mask = (df['PICKUP_DATE_TIME'].dt.date >= start_date) & (df['PICKUP_DATE_TIME'].dt.date <= end_date)

filtered_df = df.loc[mask]
filtered_df = filtered_df[['NAMA_SIGESIT', 'NAMA_GERAI', 'COURIER_INSENTIVE','Total Pickup']]
filtered_kurir = filtered_df[filtered_df['NAMA_SIGESIT'] != 'Superadmin']
filtered_kurir = filtered_kurir.groupby(['NAMA_SIGESIT','NAMA_GERAI'], as_index=False).agg({'COURIER_INSENTIVE':'sum','Total Pickup':'sum'}).sort_values(by='Total Pickup',ascending=False)

#if filtered_kurir.empty:
#    st.warning("Tidak ada data pada tanggal tersebut.")
#else:
#    st.subheader("📋 Data pada Tanggal Terpilih")
#    st.dataframe(filtered_kurir)

st.subheader("📈 Produktivitas Kurir dan SLA Pickup Performance Gerai")

# Buat dua kolom sejajar
col1, col2 = st.columns([1.2, 1])

with col1:
    st.write("📋 Tabel Insentif Kurir")
    st.dataframe(filtered_kurir)

with col2:
    # Filter SLA berdasarkan tanggal
    df_sla['PICKUP_DATE_TIME'] = pd.to_datetime(df_sla['PICKUP_DATE_TIME'])
    mask_sla = (df_sla['PICKUP_DATE_TIME'].dt.date >= start_date) & (df_sla['PICKUP_DATE_TIME'].dt.date <= end_date)
    filtered_sla = df_sla.loc[mask_sla]

    if filtered_sla.empty:
        st.warning("Tidak ada data SLA pada tanggal tersebut.")
    else:
        # Bersihkan dan pastikan kolom NAMA_GERAI valid
        filtered_sla = filtered_sla.dropna(subset=['NAMA_GERAI'])
        filtered_sla['NAMA_GERAI'] = filtered_sla['NAMA_GERAI'].astype(str).str.strip()

        # Hitung rata-rata SLA
        sla_chart_data = filtered_sla.groupby('NAMA_GERAI').agg(
            SLA_RataRata=('% SLA', 'mean')
        ).reset_index()

        # Buat chart
        chart_sla = alt.Chart(sla_chart_data).mark_line(point=True).encode(
            x=alt.X('NAMA_GERAI:N', title='Gerai', sort=None, axis=alt.Axis(labelAngle=-85)),
            y=alt.Y('SLA_RataRata:Q', title='Rata-rata SLA (%)'),
            tooltip=['NAMA_GERAI:N', 'SLA_RataRata']
        ).properties(
            width=400,
            height=300,
            title='📊 Rata-rata SLA Pickup'
        )

        st.altair_chart(chart_sla, use_container_width=True)


# Multiselect Gerai
selected_gerai = st.multiselect(
    "📍 Pilih Gerai untuk Menampilkan Kurir:",
    options=filtered_kurir['NAMA_GERAI'].unique().tolist(),
    default=filtered_kurir['NAMA_GERAI'].unique().tolist()
)

# Filter kurir berdasarkan gerai terpilih
kurir_filtered = filtered_kurir[filtered_kurir['NAMA_GERAI'].isin(selected_gerai)]

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("###ℹ️ Tabel diatas menampilkan jumlah produktifitas kurir dan insentif yang didapat pada periode tertentu, sehingga dapat dilihat Si Gesit yang mempunyai performa baik atau tidak ")
st.markdown("###ℹ️ Chart SLA Pickup Gerai menunjukan performa pickup setiap gerai pada periode tertentu untuk mengukur performa perbandingan SLA Pickup setiap Gerai  ")
# Jika kosong
if kurir_filtered.empty:
    st.warning("Tidak ada data untuk gerai yang dipilih.")
else:
    st.subheader("📊 Produtivitas Kurir Setiap Gerai ")

    # Buat label kombinasi Gerai + Kurir untuk X-Axis
    kurir_filtered['Kurir_Gerai'] = kurir_filtered['NAMA_SIGESIT'] + " (" + kurir_filtered['NAMA_GERAI'] + ")"

    # Hitung rata-rata pickup
    avg_kurir_load = kurir_filtered['Total Pickup'].mean()

    # Bar Chart
    base_kurir_chart = alt.Chart(kurir_filtered).encode(
        x=alt.X('Kurir_Gerai:N', sort='-y', title="Kurir (Gerai)"),
        y=alt.Y('Total Pickup:Q', title="Jumlah Pickup"),
        color=alt.Color('NAMA_GERAI:N', legend=alt.Legend(title="Gerai")),
        tooltip=['NAMA_SIGESIT', 'NAMA_GERAI', 'Total Pickup', 'COURIER_INSENTIVE']
    )

    bar_kurir_chart = base_kurir_chart.mark_bar()

    # Garis rata-rata
    avg_line = alt.Chart(pd.DataFrame({'y': [avg_kurir_load]})).mark_rule(
        color='red',
        strokeDash=[4, 4]
    ).encode(y='y:Q')

    full_chart = alt.layer(bar_kurir_chart, avg_line).properties(
        width=900,
        height=400
    ).configure_axisX(labelAngle=-80)

    st.altair_chart(full_chart, use_container_width=True)



top_n = st.selectbox("Tampilkan Top Gerai berdasarkan jumlah load:", [10, 20, 30], index=0)

# 🧮 AGGREGASI
# -----------------------------
agg = filtered_df.groupby('NAMA_GERAI').agg(
    Jumlah_Load=('Total Pickup', 'sum'),
    Total_Insentif=('COURIER_INSENTIVE', 'sum')
).reset_index()

# Filter top N
agg = agg.sort_values('Jumlah_Load', ascending=False).head(top_n)

# Hitung rata-rata
avg_kurir = agg['Jumlah_Load'].mean()
avg_insentif = agg['Total_Insentif'].mean()

# -----------------------------
# 🔍 TAMPILKAN TABEL
# -----------------------------
st.subheader(f"📋 Data Load dan Insentif Gerai ({start_date} s.d. {end_date})")
st.dataframe(agg)

# -----------------------------
# 📈 CHART: Bar + Line (Dual Axis)
# -----------------------------
# Chart 1: Jumlah Load per Gerai
bar_kurir_chart = alt.Chart(agg).mark_bar(color='steelblue').encode(
    x=alt.X('NAMA_GERAI:N', sort='-y', title='Nama Gerai', axis=alt.Axis(labelAngle=90)),
    y=alt.Y('Jumlah_Load:Q', title='Jumlah Load'),
    tooltip=['NAMA_GERAI', 'Jumlah_Load']
).properties(
    title='Jumlah Load per Gerai',
    width=900,
    height=300
)

avg_line_load = alt.Chart(pd.DataFrame({'y': [avg_kurir]})).mark_rule(
    color='orange', strokeDash=[4, 4]
).encode(
    y='y:Q'
)

# Chart 2: Total Insentif per Gerai
bar_insentif_chart = alt.Chart(agg).mark_bar(color='skyblue').encode(
    x=alt.X('NAMA_GERAI:N', sort='-y', title='Nama Gerai', axis=alt.Axis(labelAngle=90)),
    y=alt.Y('Total_Insentif:Q', title='Total Insentif'),
    tooltip=['NAMA_GERAI', 'Total_Insentif']
).properties(
    title='Total Insentif per Gerai',
    width=900,
    height=300
)

avg_line_insentif = alt.Chart(pd.DataFrame({'y': [avg_insentif]})).mark_rule(
    color='green', strokeDash=[4, 4]
).encode(
    y='y:Q'
)

# Gabungkan jadi 2 chart vertikal
final_chart = alt.vconcat(
    bar_kurir_chart + avg_line_load,
    bar_insentif_chart + avg_line_insentif
).configure_title(
    fontSize=14,
    anchor='start'
)

# Tampilkan chart
st.subheader("📊 Visualisasi Jumlah Load dan Insentif per Gerai")
st.altair_chart(final_chart, use_container_width=True)



