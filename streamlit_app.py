import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# Config Halaman
st.set_page_config(
    page_title="Simulasi Portofolio Saham",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Simulator Portofolio & Reinvestment Saham")
st.caption(
    "Simulasikan strategi Deposit, Cut Loss, dan Reinvest di harga bawah berdasarkan data historis.")

# --- SIDEBAR / PANEL INPUT ---
st.sidebar.header("⚙️ Parameter Simulasi")

ticker_input = st.sidebar.text_input(
    "Kode Saham (Ticker)", value="BBCA").strip().upper()
initial_deposit = st.sidebar.number_input(
    "Modal Awal / Deposit (Rp/$)", value=10000000, step=1000000)

col_date1, col_date2 = st.sidebar.columns(2)
with col_date1:
    start_date = st.date_input(
        "Tanggal Mulai", value=pd.to_datetime("2024-01-01"))
    with col_date2:
        end_date = st.date_input(
            "Tanggal Akhir", value=pd.to_datetime("2025-01-01"))

        cut_loss_pct = st.sidebar.slider(
            "Trigger Cut Loss (%)", min_value=1.0, max_value=25.0, value=5.0, step=0.5) / 100
        reinvest_drop_pct = st.sidebar.slider(
            "Reinvest (% Turun dari Cut Loss)", min_value=1.0, max_value=30.0, value=7.0, step=0.5) / 100

        btn_run = st.sidebar.button(
            "🚀 Jalankan Simulasi", use_container_width=True, type="primary")

        # Formatting Symbol (Otomatis tambah .JK jika saham Indonesia)
        symbol = ticker_input
        if not symbol.endswith(".JK") and len(symbol) == 4 and symbol.isalpha():
            symbol += ".JK"

            # --- FUNGSI SIMULASI ---
            def run_simulation(df, initial_deposit, cut_loss_pct, reinvest_drop_pct):
                cash = initial_deposit
                shares = 0
                buy_price = 0
                state = "WAITING_BUY"
                cut_loss_price = 0
                logs = []

                for date, row in df.iterrows():
                    close_price = float(
                        row['Close'])
                    date_str = date.strftime('%Y-%m-%d')

                    if state == "WAITING_BUY":
                        shares = cash / close_price
                        buy_price = close_price
                        cash = 0
                        state = "HOLDING"
                        logs.append({
                            "Tanggal": date_str,
                            "Aksi": "BUY",
                            "Harga": close_price,
                            "Keterangan": f"Beli Awal ({int(shares):,} lembar)",
                            "P/L (%)": 0.0
                        })

                        elif state == "HOLDING":
                            current_loss = (
                                close_price - buy_price) / buy_price
                            if current_loss <= -cut_loss_pct:
                                cash = shares * close_price
                                cut_loss_price = close_price
                                shares = 0
                                state = "WAITING_REINVEST"
                                logs.append({
                                    "Tanggal": date_str,
                                    "Aksi": "CUT LOSS",
                                    "Harga": close_price,
                                    "Keterangan": f"Cut Loss | Kas: Rp{cash:,.0f}",
                                    "P/L (%)": current_loss * 100
                                })

                                elif state == "WAITING_REINVEST":
                                    further_drop = (
                                        close_price - cut_loss_price) / cut_loss_price
                                    if further_drop <= -reinvest_drop_pct:
                                        shares = cash / close_price
                                        buy_price = close_price
                                        cash = 0
                                        state = "DONE"
                                        logs.append({
                                            "Tanggal": date_str,
                                            "Aksi": "REINVEST",
                                            "Harga": close_price,
                                            "Keterangan": f"Reinvest Harga Bawah ({int(shares):,} lembar)",
                                            "P/L (%)": 0.0
                                        })

                                        last_price = float(
                                            df['Close'].iloc[-1])
                                        total_value = cash if state in [
                                            "WAITING_REINVEST", "WAITING_BUY"] else (shares * last_price)

                                        return total_value, logs

                                        # --- EXECUTION & DISPLAY ---
                                        if btn_run or "simulation_done" not in st.session_state:
                                            st.session_state[
                                                "simulation_done"] = True

                                            with st.spinner(f"Mengambil data historis {symbol} dari Yahoo Finance..."):
                                                try:
                                                    df = yf.download(
                                                        symbol, start=start_date, end=end_date)

                                                    if df.empty:
                                                        st.error(
                                                            f"Data saham '{symbol}' tidak ditemukan. Pastikan kode ticker dan rentang tanggal benar.")
                                                        else:
                                                            if isinstance(df.columns, pd.MultiIndex):
                                                                df.columns = df.columns.get_level_values(
                                                                    0)

                                                                total_value, logs = run_simulation(
                                                                    df, initial_deposit, cut_loss_pct, reinvest_drop_pct)
                                                                profit_loss = total_value - initial_deposit
                                                                profit_loss_pct = (
                                                                    profit_loss / initial_deposit) * 100

                                                                # --- SUMMARY METRICS ---
                                                                col1, col2, col3 = st.columns(
                                                                    3)
                                                                col1.metric(
                                                                    "Modal Awal", f"Rp {initial_deposit:,.0f}")
                                                                col2.metric(
                                                                    "Nilai Akhir Portfolio", f"Rp {total_value:,.0f}")
                                                                col3.metric(
                                                                    "Total Return", f"{profit_loss_pct:.2f}%", delta=f"Rp {profit_loss:,.0f}")

                                                                st.divider()

                                                                # --- GRAFIK INTERAKTIF ---
                                                                st.subheader(
                                                                    "📉 Grafik Harga & Titik Eksekusi")

                                                                fig = go.Figure()
                                                                fig.add_trace(go.Scatter(
                                                                    x=df.index, y=df['Close'], mode='lines', name='Harga Closing', line=dict(color='#38bdf8', width=2)))

                                                                # Marker untuk Eksekusi Buy / Cut Loss / Reinvest
                                                                log_df = pd.DataFrame(
                                                                    logs)
                                                                if not log_df.empty:
                                                                    for _, row in log_df.iterrows():
                                                                        color = 'green' if row['Aksi'] == 'BUY' else (
                                                                            'red' if row['Aksi'] == 'CUT LOSS' else 'orange')
                                                                        symbol_shape = 'triangle-up' if row['Aksi'] in [
                                                                            'BUY', 'REINVEST'] else 'triangle-down'

                                                                        fig.add_trace(go.Scatter(
                                                                            x=[pd.to_datetime(
                                                                                row['Tanggal'])],
                                                                            y=[row['Harga']],
                                                                            mode='markers+text',
                                                                            name=row['Aksi'],
                                                                            text=[
                                                                                row['Aksi']],
                                                                            textposition="top center",
                                                                            marker=dict(
                                                                                color=color, size=12, symbol=symbol_shape),
                                                                            showlegend=False
                                                                        ))

                                                                        fig.update_layout(
                                                                            template="plotly_dark",
                                                                            height=400,
                                                                            margin=dict(
                                                                                l=20, r=20, t=30, b=20),
                                                                            xaxis_title="Tanggal",
                                                                            yaxis_title="Harga"
                                                                        )
                                                                        st.plotly_chart(
                                                                            fig, use_container_width=True)

                                                                        # --- TABEL LOG TRANSAKSI ---
                                                                        st.subheader(
                                                                            "📜 Riwayat Transaksi")
                                                                        if not log_df.empty:
                                                                            st.dataframe(
                                                                                log_df[[
                                                                                    'Tanggal', 'Aksi', 'Harga', 'Keterangan', 'P/L (%)']],
                                                                                use_container_width=True,
                                                                                hide_index=True
                                                                            )
                                                                            else:
                                                                                st.info(
                                                                                    "Tidak ada transaksi yang terpicu pada periode ini.")

                                                                                except Exception as e:
                                                                                    st.error(
                                                                                        f"Terjadi kesalahan saat memproses data: {str(e)}")
