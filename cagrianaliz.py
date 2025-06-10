import streamlit as st
import pandas as pd
import io

def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl", datetime_format='yyyy-mm-dd hh:mm:ss') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

st.set_page_config(layout="wide")
st.title("Tedarik Sürekliliği Veri Kalite Plaftormu")
st.markdown(
    """
    <style>
    .creator-banner {
        width: 100%;
        background-color: #000000;
        padding: 5px 10px;
        text-align: right;
        font-size: 18px;
        color: green;
        font-weight: bold;
    }
    </style>
    <div class="creator-banner">
        Created by @barangurkanguven
    </div>
    """,
    unsafe_allow_html=True
)
# -------------------------
# BÖLÜM 1: ARDIŞIK KESİNTİLERDE ÇAĞRI KAYDI OLANLAR
# -------------------------
st.header("1. Aynı Şebeke Unsurunda ve Ardışık Kesintilerde Aynı Kullanıcının Çağrı Kaydı Bıraktığı Kesintiler")

max_saat = st.number_input(
    "🔧 Kaç saate kadar ardışıklık kontrol edilsin? (min: 1 saniye ≈ 0.00028, max: 240 saat)",
    min_value=0.00028, max_value=240.0, value=10.0, step=0.1, key="b1"
)

file1 = st.file_uploader("📄 Cagri_List.xlsx dosyasını yükleyin", type=["xlsx"], key="f1")
if file1:
    df1 = pd.read_excel(file1, engine="openpyxl", header=2)
    df1.columns = df1.columns.str.strip()
    df1["KESINTI BASLANGIC SAATI"] = pd.to_datetime(df1["KESINTI BASLANGIC SAATI"], dayfirst=True, errors="coerce")
    df1["KESINTI BITIS SAATI"] = pd.to_datetime(df1["KESINTI BITIS SAATI"], dayfirst=True, errors="coerce")

    ardışık_kayitlar = []
    for musteri, grup in df1.groupby("MUSTERI"):
        grup = grup.sort_values("KESINTI BASLANGIC SAATI").reset_index(drop=True)
        zincir = [grup.loc[0]]
        for i in range(1, len(grup)):
            onceki = zincir[-1]
            simdiki = grup.loc[i]
            fark = (simdiki["KESINTI BASLANGIC SAATI"] - onceki["KESINTI BITIS SAATI"]).total_seconds() / 3600
            if 0 < fark <= max_saat:
                zincir.append(simdiki)
            else:
                if len(zincir) > 1:
                    satir = {"MUSTERI": musteri}
                    b1, b2 = zincir[0]["KESINTI BASLANGIC SAATI"], zincir[-1]["KESINTI BITIS SAATI"]
                    sure = (b2 - b1).total_seconds() / 3600
                    for j, z in enumerate(zincir):
                        satir[f"#{j+1} KOD"] = z["KESINTI_KOD"]
                        satir[f"#{j+1} Ş.UNSU"] = z["SEBEKE UNSURU"]
                        satir[f"#{j+1} BAŞ"] = z["KESINTI BASLANGIC SAATI"]
                        satir[f"#{j+1} BİT"] = z["KESINTI BITIS SAATI"]
                    satir["BİRLEŞİRSE SÜRE (saat)"] = round(sure, 2)
                    ardışık_kayitlar.append(satir)
                zincir = [simdiki]
        if len(zincir) > 1:
            satir = {"MUSTERI": musteri}
            b1, b2 = zincir[0]["KESINTI BASLANGIC SAATI"], zincir[-1]["KESINTI BITIS SAATI"]
            sure = (b2 - b1).total_seconds() / 3600
            for j, z in enumerate(zincir):
                satir[f"#{j+1} KOD"] = z["KESINTI_KOD"]
                satir[f"#{j+1} Ş.UNSU"] = z["SEBEKE UNSURU"]
                satir[f"#{j+1} BAŞ"] = z["KESINTI BASLANGIC SAATI"]
                satir[f"#{j+1} BİT"] = z["KESINTI BITIS SAATI"]
            satir["BİRLEŞİRSE SÜRE (saat)"] = round(sure, 2)
            ardışık_kayitlar.append(satir)
    if ardışık_kayitlar:
        df_final_ardisik_cagri = pd.DataFrame(ardışık_kayitlar)

    # Tarih sütunlarını datetime olarak formatla
    for col in df_final_ardisik_cagri.columns:
        if "BAŞ" in col or "BİT" in col:
            df_final_ardisik_cagri[col] = pd.to_datetime(df_final_ardisik_cagri[col]).dt.strftime("%Y-%m-%d %H:%M:%S")

    st.success("✅ Ardışık çağrılı kesintiler bulundu.")
    st.dataframe(df_final_ardisik_cagri)

    excel_bytes = convert_df_to_excel(df_final_ardisik_cagri)
    st.download_button(
        label="📥 Excel olarak indir (Ardışık Çağrı Kaydı Olanlar)",
        data=excel_bytes,
        file_name="ardisik_cagri_kaydi_olanlar.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Bu kriterlerde ardışık çağrı bulunamadı.")
# -------------------------
# BÖLÜM 2: MÜKERRER GRUPLAMA + KARAR + YENİ SÜRE
# -------------------------
st.markdown("---")
st.header("2. Mükerrer Kesinti Kontrolü (Aynı Şebeke Unsurunda Süre Olarak Geçişen Kesintiler)")

file2 = st.file_uploader("📄 Kesinti_List.xlsx dosyasını yükleyin", type=["xlsx"], key="f2")
if file2:
    df2 = pd.read_excel(file2, engine="openpyxl", header=2)
    df2.columns = df2.columns.str.strip()
    df2["KESINTI BASLANGIC SAATI"] = pd.to_datetime(df2["KESINTI BASLANGIC SAATI"], dayfirst=True, errors="coerce")
    df2["KESINTI BITIS SAATI"] = pd.to_datetime(df2["KESINTI BITIS SAATI"], dayfirst=True, errors="coerce")

    df2.sort_values(by=["SEBEKE UNSURU", "KESINTI BASLANGIC SAATI"], inplace=True)
    df2.reset_index(drop=True, inplace=True)

    results = []
    grup_sayac = 1

    for unsur, grup in df2.groupby("SEBEKE UNSURU"):
        grup = grup.sort_values("KESINTI BASLANGIC SAATI").reset_index(drop=True)
        zincir = []
        grup_id = f"GRUP_{grup_sayac:03d}"
        for i in range(len(grup)):
            k = grup.loc[i]
            if not zincir:
                zincir.append(k)
            else:
                if k["KESINTI BASLANGIC SAATI"] <= zincir[-1]["KESINTI BITIS SAATI"]:
                    zincir.append(k)
                else:
                    if len(zincir) > 1:
                        gb, ge = zincir[0]["KESINTI BASLANGIC SAATI"], zincir[-1]["KESINTI BITIS SAATI"]
                        sure = (ge - gb).total_seconds() / 3600
                        for j, z in enumerate(zincir):
                            karar = "MEVCUT" if j == 0 else "İPTAL"
                            results.append({
                                "GRUP ID": grup_id,
                                "SEBEKE UNSURU": unsur,
                                "KESINTI_KOD": z["KESINTI_KOD"],
                                "KESINTI BAŞ": z["KESINTI BASLANGIC SAATI"],
                                "KESINTI BİT": z["KESINTI BITIS SAATI"],
                                "GRUP BAŞ": gb,
                                "GRUP BİT": ge,
                                "KARAR": karar,
                                "YENİ SÜRE (saat)": round(sure, 2) if karar == "MEVCUT" else None
                            })
                        grup_sayac += 1
                    zincir = [k]
        if len(zincir) > 1:
            gb, ge = zincir[0]["KESINTI BASLANGIC SAATI"], zincir[-1]["KESINTI BITIS SAATI"]
            sure = (ge - gb).total_seconds() / 3600
            for j, z in enumerate(zincir):
                karar = "MEVCUT" if j == 0 else "İPTAL"
                results.append({
                    "GRUP ID": grup_id,
                    "SEBEKE UNSURU": unsur,
                    "KESINTI_KOD": z["KESINTI_KOD"],
                    "KESINTI BAŞ": z["KESINTI BASLANGIC SAATI"],
                    "KESINTI BİT": z["KESINTI BITIS SAATI"],
                    "GRUP BAŞ": gb,
                    "GRUP BİT": ge,
                    "KARAR": karar,
                    "YENİ SÜRE (saat)": round(sure, 2) if karar == "MEVCUT" else None
                })
            grup_sayac += 1
    if results:
        st.success("✅ Mükerrer gruplar oluşturuldu ve kararlar belirlendi.")

        df_final_mukerrer = pd.DataFrame(results)

    # Tarih sütunlarını datetime string formatına çevir
    for col in df_final_mukerrer.columns:
        if "BAŞ" in col or "BİT" in col:
            df_final_mukerrer[col] = pd.to_datetime(df_final_mukerrer[col]).dt.strftime("%Y-%m-%d %H:%M:%S")

    st.dataframe(df_final_mukerrer)

    excel_bytes = convert_df_to_excel(df_final_mukerrer)
    st.download_button(
        label="📥 Excel olarak indir (Mükerrer Kesinti Kontrolü)",
        data=excel_bytes,
        file_name="mukerrer_kesinti_kontrolu.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Zaman çakışması içeren kesinti grubu bulunamadı.")
# -------------------------
# BÖLÜM 3: ARDIŞIK KESİNTİLER (ÇAĞRISIZ, MÜKERRER OLMAYAN)
# -------------------------
st.markdown("---")
st.header("3. Aynı Şebeke Unsurunda Ardışık Kesinti Tespiti (Ardışıklık Saati Kullanıcı Tarafından Belirlenir)")

st.warning("Not:Bu analizi şebeke unsuru bazında zamansal kesişme durumlarını ortadan kaldırdıktan sonra çalıştırınız.")

max_gap = st.number_input(
    "⏱ Kaç saate kadar ardışık kesintiler kontrol edilsin?", min_value=0.00028, max_value=240.0, value=4.0, step=0.1, key="b3"
)

file3 = st.file_uploader("📄 Kesinti_List.xlsx dosyasını yükleyin", type=["xlsx"], key="f3")
if file3:
    df3 = pd.read_excel(file3, engine="openpyxl", header=2)
    df3.columns = df3.columns.str.strip()
    df3["KESINTI BASLANGIC SAATI"] = pd.to_datetime(df3["KESINTI BASLANGIC SAATI"], dayfirst=True, errors="coerce")
    df3["KESINTI BITIS SAATI"] = pd.to_datetime(df3["KESINTI BITIS SAATI"], dayfirst=True, errors="coerce")

    df3.sort_values(by=["SEBEKE UNSURU", "KESINTI BASLANGIC SAATI"], inplace=True)
    gruplu_sonuclar = []
    grup_sayac = 1

    for unsur, grup in df3.groupby("SEBEKE UNSURU"):
        grup = grup.sort_values("KESINTI BASLANGIC SAATI").reset_index(drop=True)
        zincir = [grup.loc[0]]

        for i in range(1, len(grup)):
            onceki = zincir[-1]
            simdiki = grup.loc[i]
            fark = (simdiki["KESINTI BASLANGIC SAATI"] - onceki["KESINTI BITIS SAATI"]).total_seconds() / 3600
            if 0 < fark <= max_gap:
                zincir.append(simdiki)
            else:
                if len(zincir) > 1:
                    grup_id = f"GRUP_{grup_sayac:03d}"
                    yeni_bit = zincir[-1]["KESINTI BITIS SAATI"]
                    yeni_sure = (yeni_bit - zincir[0]["KESINTI BASLANGIC SAATI"]).total_seconds() / 3600
                    for j, z in enumerate(zincir):
                        gruplu_sonuclar.append({
                            "GRUP ID": grup_id,
                            "SEBEKE UNSURU": unsur,
                            "KESINTI_KOD": z["KESINTI_KOD"],
                            "MEVCUT BAŞLANGIÇ": z["KESINTI BASLANGIC SAATI"],
                            "MEVCUT BİTİŞ": z["KESINTI BITIS SAATI"],
                            "KARAR": "MEVCUT" if j == 0 else "İPTAL",
                            "YENİ BİTİŞ (sadece MEVCUT için)": yeni_bit if j == 0 else None,
                            "YENİ SÜRE (saat)": round(yeni_sure, 2) if j == 0 else None
                        })
                    grup_sayac += 1
                zincir = [simdiki]

        if len(zincir) > 1:
            grup_id = f"GRUP_{grup_sayac:03d}"
            yeni_bit = zincir[-1]["KESINTI BITIS SAATI"]
            yeni_sure = (yeni_bit - zincir[0]["KESINTI BASLANGIC SAATI"]).total_seconds() / 3600
            for j, z in enumerate(zincir):
                gruplu_sonuclar.append({
                    "GRUP ID": grup_id,
                    "SEBEKE UNSURU": unsur,
                    "KESINTI_KOD": z["KESINTI_KOD"],
                    "ORJ. BAŞLANGIÇ": z["KESINTI BASLANGIC SAATI"],
                    "ORJ. BİTİŞ": z["KESINTI BITIS SAATI"],
                    "KARAR": "MEVCUT" if j == 0 else "İPTAL",
                    "YENİ BİTİŞ (sadece MEVCUT için)": yeni_bit if j == 0 else None,
                    "YENİ SÜRE (saat)": round(yeni_sure, 2) if j == 0 else None
                })
            grup_sayac += 1

    if gruplu_sonuclar:
        st.success("🔁 Ardışık ama çakışmayan kesintiler gruplanarak mevcut/iptal ayrımı yapıldı.")

    df_final_ardisik_cagri_olmayan = pd.DataFrame(gruplu_sonuclar)

    # Tarih sütunlarını datetime string formatına çevir
    for col in df_final_ardisik_cagri_olmayan.columns:
        if "BAŞ" in col or "BİT" in col:
            df_final_ardisik_cagri_olmayan[col] = pd.to_datetime(df_final_ardisik_cagri_olmayan[col]).dt.strftime("%Y-%m-%d %H:%M:%S")

    st.dataframe(df_final_ardisik_cagri_olmayan)

    excel_bytes = convert_df_to_excel(df_final_ardisik_cagri_olmayan)
    st.download_button(
        label="📥 Excel olarak indir (Ardışık Çağrı Kaydı Olmayanlar)",
        data=excel_bytes,
        file_name="ardisik_cagri_kaydi_olmayanlar.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Belirtilen ardışıklık süresi içerisinde ardışık kesinti zinciri bulunamadı.")
# -------------------------
# BÖLÜM 4: ZİNCİRLEME ARDIŞIK KESİNTİLERDE AYNI MÜŞTERİNİN ÇAĞRI BIRAKMASI
# -------------------------

st.markdown("---")
st.header("4. Zincirleme Ardışık Kesintilerde Aynı Müşterinin Çağrı Bırakması")

st.warning("Not: Bu analizde bir kesinti bittikten sonraki X saat içinde aynı müşterinin çağrı bırakma durumu grup halinde raporlanmaktadır. Sorgu şebeke unsuru eşleşmesi şartı aramaz.")

# X saat input
x_saat = st.number_input(
    "🔄 Bir kesintiden sonraki kaç saat içindeki kesintiler için aramalar kontrol edilsin?",
    min_value=0.1, max_value=240.0, value=10.0, step=0.1, key="b4"
)

# Dosya yükleme
file4_cagri = st.file_uploader("📄 Cagri_List_v2.xlsx dosyasını yükleyin", type=["xlsx"], key="f4_cagri")
file4_kesinti = st.file_uploader("📄 Kesinti_List_v2.xlsx dosyasını yükleyin", type=["xlsx"], key="f4_kesinti")

if file4_cagri and file4_kesinti:
    df_cagri = pd.read_excel(file4_cagri, engine="openpyxl", header=2)
    df_kesinti = pd.read_excel(file4_kesinti, engine="openpyxl", header=2)

    # Zaman formatlama
    df_cagri["KESINTI BASLANGIC SAATI"] = pd.to_datetime(df_cagri["KESINTI BASLANGIC SAATI"], dayfirst=True, errors="coerce")
    df_cagri["KESINTI BITIS SAATI"] = pd.to_datetime(df_cagri["KESINTI BITIS SAATI"], dayfirst=True, errors="coerce")
    df_cagri["CAGRI_SAATI"] = pd.to_datetime(df_cagri["CAGRI_SAATI"], dayfirst=True, errors="coerce")

    # Kesinti Listesi'ndeki KESINTI_KOD'ları set olarak al
    kesinti_kodlar_set = set(df_kesinti["KESINTI_KOD"].unique())

    # Her müşteri için zincirleme ardışık kontrol
    ardışık_kayitlar = []
    grup_sayac = 1

    for musteri, grup in df_cagri.groupby("MUSTERI"):
        grup = grup.sort_values("KESINTI BASLANGIC SAATI").reset_index(drop=True)

        aktif_grup_id = None
        aktif_grup_bitis = None

        for i in range(len(grup)):
            k = grup.loc[i]

            if aktif_grup_id is None:
                # İlk kesinti → yeni grup başlat
                aktif_grup_id = f"GRUP_{grup_sayac:03d}"
                aktif_grup_bitis = k["KESINTI BITIS SAATI"]
                grup_sayac += 1
            else:
                # Yeni kesinti aktif grubun bitişinden X saat içinde mi?
                fark_saat = (k["KESINTI BASLANGIC SAATI"] - aktif_grup_bitis).total_seconds() / 3600

                if fark_saat <= x_saat and fark_saat >= 0:
                    # Aynı grup içinde kal
                    aktif_grup_bitis = max(aktif_grup_bitis, k["KESINTI BITIS SAATI"])
                else:
                    # Yeni grup başlat
                    aktif_grup_id = f"GRUP_{grup_sayac:03d}"
                    aktif_grup_bitis = k["KESINTI BITIS SAATI"]
                    grup_sayac += 1

            # Bu kesintiyi ilgili grup ile kaydedelim
            ardışık_kayitlar.append({
                "GRUP ID": aktif_grup_id,
                "MUSTERI": musteri,
                "KESINTI_KOD": k["KESINTI_KOD"],
                "KESINTI_BASLANGIC": k["KESINTI BASLANGIC SAATI"],
                "KESINTI_BITIS": k["KESINTI BITIS SAATI"],
                "KESINTI_VAR_MI": "VAR" if k["KESINTI_KOD"] in kesinti_kodlar_set else "YOK",
                "CAGRI_NO": k["CAGRI_NO"],
                "CAGRI_SAATI": k["CAGRI_SAATI"],
                "CAGRI_MAHALLE": k["CAGRI_MAHALLE"],
                "CAGRI_IL": k["CAGRI_IL"],
                "CAGRI_ILCE": k["CAGRI_ILCE"],
                "CAGRI_ACIKLAMA": k["CAGRI_ACIKLAMA"]
            })

    # Sonucu DataFrame olarak gösterelim
    if ardışık_kayitlar:
        df_final_zincir_ayni_musteri = pd.DataFrame(ardışık_kayitlar)

        # Tarih kolonlarını string formatına çevir → Numbers uyumlu olsun
        for col in df_final_zincir_ayni_musteri.columns:
            if "BASLANGIC" in col or "BITIS" in col or "CAGRI_SAATI" in col:
                df_final_zincir_ayni_musteri[col] = pd.to_datetime(df_final_zincir_ayni_musteri[col]).dt.strftime("%Y-%m-%d %H:%M:%S")

        st.dataframe(df_final_zincir_ayni_musteri)

        excel_bytes = convert_df_to_excel(df_final_zincir_ayni_musteri)
        st.download_button(
            label="📥 Excel olarak indir (Zincirleme Ardışık Kesintilerde Aynı Müşteri Çağrıları)",
            data=excel_bytes,
            file_name="zincirleme_ardisik_kesintiler_ayni_musteri_cagrilar.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Belirtilen süre içinde zincirleme ardışık kesinti için aynı müşteri tarafından bırakılan çağrı bulunamadı.")
else:
    st.info("Lütfen hem Çağrı Listesini hem de Kesinti Listesini yükleyin.")
