from pyspark.sql import functions as F

NULL_TOKENS = r"(?i)^\s*(nd|nan|na|n/a|none|not done|unknown|-|\.)?\s*$"
DATE_FORMATS = [
    "yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd", "dd/MM/yyyy", "dd-MM-yyyy",
    "dd MMMM yyyy", "dd/MM/yy", "dd-MM-yy", "MM/dd/yyyy",
]

def clean_id(df, c="pt_id"):
    s = F.upper(F.trim(F.col(c)))
    return df.withColumn(c, F.when(s.startswith("SP"), s)
                             .otherwise(F.concat(F.lit("SP"), s)))

def parse_date(df, c, lo="2000-01-01", hi="2026-12-31"):
    attempts = [F.to_date(F.expr(f"try_to_timestamp(trim(`{c}`), '{fmt}')"))
                for fmt in DATE_FORMATS]
    parsed = F.coalesce(*attempts)
    # two-digit years are read as 20yy; shift back a century if that is out of range
    parsed = F.when(parsed > F.lit(hi), F.add_months(parsed, -1200)).otherwise(parsed)
    valid = F.when((parsed >= F.lit(lo)) & (parsed <= F.lit(hi)), parsed)
    return df.withColumn(f"{c}_raw", F.col(c)).withColumn(c, valid)

def parse_number(df, c, keep_flag=False):
    df = (df.withColumn("_t", F.trim(F.col(c)))
            .withColumn("_lim", F.regexp_extract("_t", r"<\s*([0-9.]+)", 1)))
    value = (F.when(F.col("_t").rlike(NULL_TOKENS), F.lit(None).cast("double"))
              .when(F.col("_lim") != "", F.expr("try_cast(_lim as double)") / 2)
              .otherwise(F.expr("try_cast(_t as double)")))
    if keep_flag:
        df = df.withColumn(f"{c}_censored", F.col("_lim") != "")
    return df.withColumn(c, value).drop("_t", "_lim")

def null_outside(df, c, lo, hi):
    col = F.col(c)
    return df.withColumn(c, F.when((col >= lo) & (col <= hi), col))

def map_values(df, c, mapping, keep_unmapped=True):
    key = F.lower(F.trim(F.col(c)))
    lookup = F.create_map(*[F.lit(x) for kv in mapping.items() for x in kv])
    mapped = F.try_element_at(lookup, key)
    fallback = F.trim(F.col(c)) if keep_unmapped else F.lit(None)
    return df.withColumn(c, F.coalesce(mapped, fallback))

def report_unmapped(df, c, mapping):
    key = F.lower(F.trim(F.col(c)))
    return (df.filter(F.col(c).isNotNull() & ~key.isin(list(mapping)))
              .groupBy(c).count().orderBy(F.desc("count")))

# Lookup tables: keys must be lower case.
SEX = {"m": "Male", "male": "Male", "f": "Female", "female": "Female"}
YES_NO = {"y": "Yes", "yes": "Yes", "n": "No", "no": "No"}
SMEAR = {
    "neg": "Negative", "negative": "Negative", "0": "Negative",
    "scant": "Scanty", "scanty": "Scanty",
    "one plus": "1+", "1 +": "1+", "1+": "1+", "+1": "1+",
    "two plus": "2+", "2 +": "2+", "2+": "2+", "+2": "2+",
    "three plus": "3+", "3 +": "3+", "3+": "3+", "+3": "3+",
}
CXR = {
    "nad": "Normal", "normal": "Normal", "no abnormality": "Normal",
    "infiltrate": "Infiltrate", "consolidation": "Consolidation",
    "infiltrate/consolidation": "Infiltrate/Consolidation",
    "cavitation": "Cavitation", "cavitary": "Cavitation", "cavity noted": "Cavitation",
    "pleural effusion": "Pleural effusion", "fibrosis": "Fibrosis",
    "other": "Other", "other abnormality": "Other", "abnormal - other": "Other",
}
OUTCOME_GROUP = {
    "cured": "favourable", "treatment completed": "favourable",
    "completed": "favourable", "tx completed": "favourable",
    "died": "unfavourable", "deceased": "unfavourable",
    "failed": "unfavourable", "treatment failed": "unfavourable",
    "lost to follow up": "unfavourable", "lost to follow-up": "unfavourable",
    "lost to followup": "unfavourable", "lost to f/u": "unfavourable",
    "ltfu": "unfavourable",
}   # "not evaluated", "unknown" and "nd" stay null and leave the model.