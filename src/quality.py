from pyspark.sql import functions as F

def assert_unique(df, cols):
    cols = [cols] if isinstance(cols, str) else cols
    n = df.groupBy(*cols).count().filter("count > 1").count()
    assert n == 0, f"{n} duplicated keys in {cols}"

def unparsed_dates(df, c):
    """Rows where a date existed in the source but could not be parsed."""
    return df.filter(F.col(c).isNull() & F.col(f"{c}_raw").isNotNull()).count()

def null_report(df):
    total = df.count()
    row = df.select([
        F.round(F.sum(F.col(c).isNull().cast("int")) / total * 100, 1).alias(c)
        for c in df.columns
    ]).first()
    return {c: row[c] for c in df.columns}