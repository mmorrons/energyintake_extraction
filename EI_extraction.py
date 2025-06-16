import streamlit as st
import pandas as pd
import pdfplumber
import re
import io
import os


# --- Core Extraction Logic (Complete and Corrected) ---

def extract_statistics(text):
    """
    Estrae i dati dalla sezione "Statistiche" del PDF.
    Gestisce con robustezza l'assenza di dati.
    (Input text should be normalized: no thousands separators, '.' as decimal)
    """
    statistics = {
        "Diff_TDEE_kcal": None,
        "Diff_TDEE_pct": None,
        "Diff_BMR_kcal": None,
        "Diff_BMR_pct": None,
        "Protein_per_kg_actual_g": None,
        "Kcal_per_kg_actual_kcal": None,
        "Protein_per_kg_ideal_g": None,
        "Kcal_per_kg_ideal_kcal": None,
    }

    try:
        # Patterns updated to expect normalized numbers (e.g., 1234.56)
        tdee_match = re.search(r"Differenza dal TDEE:\s*([\d.]+)\s*kcal\s*\(([\d.]+)\s*%\)", text)
        if tdee_match:
            statistics["Diff_TDEE_kcal"] = float(tdee_match.group(1))
            statistics["Diff_TDEE_pct"] = float(tdee_match.group(2))

        bmr_match = re.search(r"Differenza dal BMR:\s*([\d.]+)\s*kcal\s*\(([\d.]+)\s*%\)", text)
        if bmr_match:
            statistics["Diff_BMR_kcal"] = float(bmr_match.group(1))
            statistics["Diff_BMR_pct"] = float(bmr_match.group(2))

        protein_actual_match = re.search(r"Proteine per kg di peso attuale:\s*([\d.]+)\s*g", text)
        if protein_actual_match:
            statistics["Protein_per_kg_actual_g"] = float(protein_actual_match.group(1))

        kcal_actual_match = re.search(r"kcal per kg di peso attuale:\s*([\d.]+)\s*kcal", text)
        if kcal_actual_match:
            statistics["Kcal_per_kg_actual_kcal"] = float(kcal_actual_match.group(1))

        protein_ideal_match = re.search(r"Proteine per kg di peso ideale BMI:\s*([\d.]+)\s*g", text)
        if protein_ideal_match:
            statistics["Protein_per_kg_ideal_g"] = float(protein_ideal_match.group(1))

        kcal_ideal_match = re.search(r"kcal per kg di peso ideale BMI:\s*([\d.]+)\s*kcal", text)
        if kcal_ideal_match:
            statistics["Kcal_per_kg_ideal_kcal"] = float(kcal_ideal_match.group(1))

    except Exception as e:
        st.error(f"Error extracting statistics: {e}")

    return statistics


def extract_all_variables_from_pdf(uploaded_file):
    """
    Main orchestration function. Extracts all data from a single PDF.
    """
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=2)
                if page_text:
                    text += page_text + "\n"

        text_for_display = text.replace("\n", " ").strip()
        text_normalized = text_for_display.replace(".", "").replace(",", ".")

        data = {}

        # General info can parse from normalized text, but names/dates are safer from original
        general_info = extract_general_information(text_for_display, text_normalized)
        data.update(general_info)

        # Use the NORMALIZED text for all functions that parse numbers
        statistics = extract_statistics(text_normalized)
        data.update(statistics)

        weight_kg = general_info.get("Weight_kg")

        macronutrients = extract_macronutrient_values_from_grams(text_normalized, weight_kg)
        data.update(macronutrients)

        minerals = extract_minerals(text_normalized)
        data.update(minerals)

        vitamins = extract_vitamins(text_normalized)
        data.update(vitamins)

        amino_acids = extract_amino_acids(text_normalized)
        data.update(amino_acids)

        fatty_acids = extract_fatty_acids(text_normalized)
        data.update(fatty_acids)

        ratios_and_indices = extract_ratios_and_indices(text_normalized)
        data.update(ratios_and_indices)

        inq_values = extract_inq_values(text_normalized)
        data.update(inq_values)

        return data

    except Exception as e:
        st.error(f"Critical error processing file {uploaded_file.name}: {e}")
        return None


def extract_general_information(original_text, normalized_text):
    """
    Extracts general patient information.
    Uses original text for names/dates and normalized for numbers.
    """
    general_info = {
        "Patient_Name": None, "Visit_Date": None, "Gender": None, "Age_years": None,
        "Height_cm": None, "Weight_kg": None, "BMI": None, "BSA_m2": None,
        "BMR_kcal": None, "TDEE_kcal": None,
    }
    try:
        name_match = re.search(r"Report del Calcolo intake alimentare\s+([A-Za-z\s]+?)\s+Visita del", original_text)
        if name_match:
            general_info["Patient_Name"] = name_match.group(1).strip()

        date_match = re.search(r"Visita del:\s*(\d{1,2}/\d{1,2}/\d{4})", original_text)
        if date_match:
            general_info["Visit_Date"] = date_match.group(1).strip()

        gender_match = re.search(r"Sesso:\s*(Femmina|Maschio)", original_text, re.IGNORECASE)
        if gender_match:
            general_info["Gender"] = 0 if gender_match.group(1) == "Femmina" else 1

        # Use normalized text for all numeric values
        age_match = re.search(r"Età:\s*(\d+)", normalized_text)
        if age_match:
            general_info["Age_years"] = int(age_match.group(1))

        height_match = re.search(r"Altezza:\s*cm\s*(\d+)", normalized_text)
        if height_match:
            general_info["Height_cm"] = int(height_match.group(1))

        weight_match = re.search(r"Peso:\s*kg\s*([\d.]+)", normalized_text)
        if weight_match:
            general_info["Weight_kg"] = float(weight_match.group(1))

        bmi_match = re.search(r"BMI \(Body Mass Index\)\s*([\d.]+)", normalized_text)
        if bmi_match:
            general_info["BMI"] = float(bmi_match.group(1))

        bsa_match = re.search(r"BSA \(Body Surface Area\)\s*m²\s*([\d.]+)", normalized_text)
        if bsa_match:
            general_info["BSA_m2"] = float(bsa_match.group(1))

        bmr_match = re.search(r"BMR \(Basal Metabolic Rate\)\s*kcal\s*([\d.]+)", normalized_text)
        if bmr_match:
            general_info["BMR_kcal"] = float(bmr_match.group(1))

        tdee_match = re.search(r"TDEE \(Total Daily Energy Expenditure\):\s*kcal\s*([\d.]+)", normalized_text)
        if tdee_match:
            general_info["TDEE_kcal"] = float(tdee_match.group(1))

    except Exception as e:
        st.error(f"Error extracting general information: {e}")
    return general_info


def extract_macronutrient_values_from_grams(text, weight_kg):
    macronutrients = {
        "Protein_g": 0.0, "Protein_kcal": 0.0, "Protein_pct": 0.0,
        "Carbs_g": 0.0, "Carbs_kcal": 0.0, "Carbs_pct": 0.0,
        "Fats_g": 0.0, "Fats_kcal": 0.0, "Fats_pct": 0.0,
        "Alcohol_g": 0.0, "Alcohol_kcal": 0.0, "Alcohol_pct": 0.0,
        "Total_kcal": 0.0, "kcal_per_kg": None, "Protein_animal_g": None,
        "Protein_veg_g": None, "Cholesterol_mg": None, "Sugar_simple_g": None,
        "Sugar_complex_g": None, "Fiber_g": None, "Water_g": None,
    }
    try:
        macronutrient_section = re.search(r"MACRONUTRIENTI(.*?)VITAMINE", text, re.DOTALL)
        if macronutrient_section:
            section_text = macronutrient_section.group(1)

            patterns = {
                "Protein_g": r"Protidi g ([\d.]+)", "Carbs_g": r"Glucidi g ([\d.]+)",
                "Fats_g": r"Lipidi g ([\d.]+)", "Alcohol_g": r"Alcool g ([\d.]+)",
                "Protein_animal_g": r"Proteine animali g ([\d.]+)", "Protein_veg_g": r"Proteine vegetali g ([\d.]+)",
                "Cholesterol_mg": r"Colesterolo mg ([\d.]+)", "Sugar_simple_g": r"Zuccheri semplici g ([\d.]+)",
                "Sugar_complex_g": r"Zuccheri complessi g ([\d.]+)", "Fiber_g": r"Fibra g ([\d.]+)",
                "Water_g": r"Acqua g ([\d.]+)",
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, section_text)
                if match:
                    macronutrients[key] = float(match.group(1))

            macronutrients["Protein_kcal"] = macronutrients["Protein_g"] * 4
            macronutrients["Carbs_kcal"] = macronutrients["Carbs_g"] * 4
            macronutrients["Fats_kcal"] = macronutrients["Fats_g"] * 9
            macronutrients["Alcohol_kcal"] = macronutrients["Alcohol_g"] * 7

            total_kcal = (macronutrients["Protein_kcal"] + macronutrients["Carbs_kcal"] +
                          macronutrients["Fats_kcal"] + macronutrients["Alcohol_kcal"])
            macronutrients["Total_kcal"] = total_kcal

            if total_kcal > 0:
                macronutrients["Protein_pct"] = (macronutrients["Protein_kcal"] / total_kcal) * 100
                macronutrients["Carbs_pct"] = (macronutrients["Carbs_kcal"] / total_kcal) * 100
                macronutrients["Fats_pct"] = (macronutrients["Fats_kcal"] / total_kcal) * 100
                macronutrients["Alcohol_pct"] = (macronutrients["Alcohol_kcal"] / total_kcal) * 100

            if total_kcal and weight_kg:
                macronutrients["kcal_per_kg"] = round(total_kcal / weight_kg, 2)
    except Exception as e:
        st.error(f"Error extracting macronutrient values: {e}")
    return macronutrients


def extract_minerals(text):
    minerals = {}
    mineral_keywords = {
        "Calcio": "mg", "Cromo": "µg", "Ferro": "mg", "Fluoruri": "µg", "Fosforo": "mg",
        "Iodio": "µg", "Magnesio": "mg", "Manganese": "mg", "Molibdeno": "µg", "Potassio": "mg",
        "Rame": "mg", "Selenio": "µg", "Sodio": "mg", "Zinco": "mg",
    }
    for mineral, unit in mineral_keywords.items():
        key = f"{mineral}_{unit}"
        pattern = fr"{mineral}\s+{unit}\s+([\d.]+)"
        match = re.search(pattern, text)
        minerals[key] = float(match.group(1)) if match else None
    return minerals


def extract_vitamins(text):
    vitamins = {}
    vitamin_keywords = {
        "Acido pantotenico": "mg", "β-Carotene": "µg", "Biotina": "µg", "Folati": "µg",
        "Niacina": "mg", "α-Tocoferolo": "mg", "Vitamina A": "µg RE", "Vitamina B1": "mg",
        "Vitamina B2": "mg", "Vitamina B6": "mg", "Vitamina B12": "µg", "Vitamina C": "mg",
        "Vitamina D": "µg", "Vitamina E": "mg TE", "Vitamina K": "µg",
    }
    for vitamin, unit in vitamin_keywords.items():
        key = f"{vitamin}_{unit.replace(' ', '_')}"
        pattern = fr"{vitamin}\s+{unit}\s+([\d.]+)"
        match = re.search(pattern, text)
        vitamins[key] = float(match.group(1)) if match else None
    return vitamins


def extract_amino_acids(text):
    amino_acids = {}
    amino_acid_keywords = {
        "Aspartic_mg": "Acido aspartico", "Glutamic_mg": "Acido glutamico", "Alanine_mg": "Alanina",
        "Arginine_mg": "Arginina", "Cysteine_mg": "Cisteina", "Phenylalanine_mg": "Fenilalanina",
        "Glycine_mg": "Glicina", "Isoleucine_mg": "Isoleucina", "Histidine_mg": "Istidina",
        "Leucine_mg": "Leucina", "Lysine_mg": "Lisina", "Methionine_mg": "Metionina",
        "Proline_mg": "Prolina", "Serine_mg": "Serina", "Threonine_mg": "Treonina",
        "Tyrosine_mg": "Tirosina", "Tryptophan_mg": "Triptofano", "Valine_mg": "Valina",
    }
    for key, keyword in amino_acid_keywords.items():
        pattern = fr"{keyword}\s*mg\s*([\d.]+)"
        match = re.search(pattern, text)
        amino_acids[key] = float(match.group(1)) if match else None
    return amino_acids


def extract_fatty_acids(text):
    fatty_acids = {}
    fatty_acid_keywords = {
        "Saturated": "Acidi grassi saturi", "Unsaturated": "Acidi grassi insaturi",
        "MonoUnsaturated": "Acidi grassi monoinsaturi", "PolyUnsaturated": "Acidi grassi polinsaturi",
        "Lauric": "Acido laurico", "Myristic": "Acido miristico", "Palmitic": "Acido palmitico",
        "OtherSaturated": "Altri acidi grassi saturi", "Oleic": "Acido oleico",
        "OtherMonounsaturated": "Altri acidi grassi monoinsaturi", "Linoleic": "Acido linoleico",
        "Linolenic": "Acido linolenico", "EPA": "Acido eicosapentaenoico",
        "DHA": "Acido docosaesaenoico", "Omega6": "AGPn-6", "Omega3": "AGPn-3",
    }
    for key, keyword in fatty_acid_keywords.items():
        pattern = fr"{keyword}\s*g\s*([\d.]+)"
        match = re.search(pattern, text)
        fatty_acids[key] = float(match.group(1)) if match else None
    return fatty_acids


def extract_ratios_and_indices(text):
    ratios_and_indices = {}
    keywords = {
        "Saturated_Unsaturated": "Acidi grassi saturi / insaturi",
        "Mono_Poli_Unsaturated": "Acidi grassi monoinsaturi / polinsaturi",
        "Animal_Vegetable": "Proteine animali / vegetali",
        "MAI": "MAI - Adeguatezza mediterranea", "IA": "IA - Aterogenicità",
        "IT": "IT - Trombogenicità", "CSI": "CSI - Colesterolo-acidi grassi saturi",
    }
    for key, keyword in keywords.items():
        pattern = fr"{re.escape(keyword)}\s*([\d.]+)"
        match = re.search(pattern, text)
        ratios_and_indices[key] = float(match.group(1)) if match else None
    return ratios_and_indices


def extract_inq_values(text):
    inq_values = {}
    inq_keywords = {
        "INQ_Ca": "Calcio", "INQ_Fe": "Ferro", "INQ_Folati": "Folati", "INQ_P": "Fosforo",
        "INQ_Mg": "Magnesio", "INQ_Mo": "Molibdeno", "INQ_Niacina": "Niacina",
        "INQ_Prot": "Protidi", "INQ_Cu": "Rame", "INQ_Se": "Selenio", "INQ_VitA": "Vitamina A",
        "INQ_VitB1": r"Vitamina B1\b", "INQ_VitB12": r"Vitamina B12\b", "INQ_VitB2": "Vitamina B2",
        "INQ_VitB6": "Vitamina B6", "INQ_VitC": "Vitamina C", "INQ_VitD": "Vitamina D",
        "INQ_Zn": "Zinco",
    }
    for key, keyword in inq_keywords.items():
        pattern = fr"\b{keyword}\s*([\d.]+)"
        match = re.search(pattern, text)
        inq_values[key] = float(match.group(1)) if match else None
    return inq_values


# --- Streamlit UI and Application Flow ---

def main():
    """
    Main function to run the Streamlit application.
    """
    st.set_page_config(page_title="Intake Alimentare", layout="wide")
    st.title("Estrazione Intake Alimentare da Diari Nutrizionali ")
    st.markdown("Carica uno o più file .PDF generati con il software di analisi da scaricare in formato excel")

    uploaded_files = st.file_uploader(
        "Scegli i file PDF",
        type="pdf",
        accept_multiple_files=True
    )

    if not uploaded_files:
        st.info("Per favore, carica i file per iniziare")
        return

    st.markdown(f"**{len(uploaded_files)} file(s) selected:**")
    for file in uploaded_files:
        st.write(f"- `{file.name}`")

    if st.button("Clicca per estrarre i dati", type="primary"):
        all_data = []

        with st.spinner('Processamento in corso... Attendi.'):
            for uploaded_file in uploaded_files:
                st.info(f"File in processamento: {uploaded_file.name}")
                data = extract_all_variables_from_pdf(uploaded_file)
                if data:
                    all_data.append(data)

        if all_data:
            st.success("✅ Estrazione dati completata!")

            df = pd.DataFrame(all_data)

            patient_info_cols = ['Patient_Name', 'Visit_Date', 'Gender', 'Age_years', 'Height_cm', 'Weight_kg', 'BMI']
            existing_patient_cols = [col for col in patient_info_cols if col in df.columns]
            other_cols = [col for col in df.columns if col not in existing_patient_cols]
            df = df[existing_patient_cols + other_cols]

            st.markdown("### Anteprima dati estratti")
            st.dataframe(df.style.format(precision=2, na_rep='N/A'))

            # --- Download Button ---
            output = io.BytesIO()
            # Let pandas choose the best available engine. Install with `pip install openpyxl` or `pip install xlsxwriter`
            df.to_excel(output, index=False, sheet_name='ExtractedData', float_format="%.2f")
            excel_data = output.getvalue()

            st.download_button(
                label="📥 Scarica il file excel",
                data=excel_data,
                file_name="nutrition_data_extracted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ Nessun valore è stato estratto. Controlla il formato e il contenuto del file .pdf")

        st.caption(
            "Creato da: Marco Morrone, Università degli Studi di Sassari MIT license, 2025 - Per contatti: [mmorrone@uniss.it](mailto:mmorrone@uniss.it)")

if __name__ == "__main__":
    main()
