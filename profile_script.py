import pandas as pd
import numpy as np
import sys
import os

path = r'data/raw/state_CA.csv'
print('Reading CSV...')
df = pd.read_csv(path, low_memory=False, dtype=str)  # read all as string to avoid type inference issues
print('Shape:', df.shape)
print('Columns:', df.columns.tolist())
print('\nFirst few rows:')
print(df.head())

# Determine data types per pandas infer
print('\nInferred dtypes:')
print(df.dtypes)

# Count missing (including empty strings or 'NA' string)
# Replace NA strings with NaN
df_replace = df.replace('NA', np.nan)
missing_counts = df_replace.isnull().sum()
missing_pct = (missing_counts / len(df)) * 100
missing_df = pd.DataFrame({'missing_count': missing_counts, 'missing_pct': missing_pct})
print('\nMissing values (top 20):')
print(missing_df.sort_values('missing_pct', ascending=False).head(20))

# Unique counts for categorical columns (object)
cat_cols = df.select_dtypes(include=['object']).columns
print('\nUnique counts for categorical columns (top 20):')
uniq_counts = df[cat_cols].nunique().sort_values(ascending=False)
print(uniq_counts.head(20))

# Potential primary key uniqueness: check combination of activity_year, lei, loan_number (if exists)
if {'activity_year','lei','loan_number'} <= set(df.columns):
    combo = df[['activity_year','lei','loan_number']].drop_duplicates()
    print('\nUnique combinations of activity_year, lei, loan_number:', combo.shape[0])
    print('Total rows:', df.shape[0])
    if combo.shape[0] == df.shape[0]:
        print('Candidate PK: activity_year + lei + loan_number is unique')
    else:
        print('Duplicates present in combo')
else:
    print('Columns for composite key not found')

# Sample values for some coded fields
coded_fields = ['derived_ethnicity','derived_race','derived_sex','action_taken','loan_type','loan_purpose','lien_status']
for f in coded_fields:
    if f in df.columns:
        print(f'\nValue counts for {f}:')
        print(df[f].value_counts(dropna=False).head())