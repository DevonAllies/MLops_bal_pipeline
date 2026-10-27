from pathlib import Path

import joblib
import streamlit as st

st.set_page_config(page_title="TB outcome demo", layout="centered")
st.title("TB treatment outcome: workflow demo")
st.warning("All data behind this model are simulated. This app demonstrates a "
           "data pipeline and model deployment. It is not a clinical tool.")

@st.cache_resource
def load():
    return joblib.load(Path(__file__).parent / "model.joblib")

bundle = load()
model, row = bundle["model"], bundle["defaults"].copy()

c1, c2 = st.columns(2)
row["age_years"] = float(c1.number_input("Age (years)", 10, 90, 35))
row["sex"] = c1.selectbox("Sex", ["Female", "Male"])
row["hiv_status"] = c1.selectbox("HIV status", ["Negative", "Positive"])
row["genexpert_rif"] = c2.selectbox("GeneXpert rifampicin result",
                                    ["Sensitive", "Resistant", "Indeterminate"])
row["smear_grade"] = c2.selectbox("Smear grade", ["Negative", "Scanty", "1+", "2+", "3+"])
row["bmi"] = float(c2.number_input("BMI", 10.0, 50.0, 22.0))

p = float(model.predict_proba(row)[0, 1])
st.metric("Estimated chance of a favourable outcome", f"{p:.0%}")
st.caption("Training-set base rate is about 77%. The model is only modestly better "
           "than always predicting a favourable outcome.")