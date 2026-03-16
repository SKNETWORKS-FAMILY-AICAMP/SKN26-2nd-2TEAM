import os
import numpy as np
import pandas as pd

# --------------------------------------------------
# 0. 출력 옵션 설정
# --------------------------------------------------
pd.set_option("display.max_columns", 200)
pd.set_option("display.width", 200)

# --------------------------------------------------
# 1. 폴더 경로 설정
# --------------------------------------------------
current_file_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(current_file_dir)

raw_dir = os.path.join(base_dir, "data", "raw")
processed_dir = os.path.join(base_dir, "data", "processed")
os.makedirs(processed_dir, exist_ok=True)

print("current_file_dir:", current_file_dir)
print("base_dir:", base_dir)
print("raw_dir:", raw_dir)
print("processed_dir:", processed_dir)

# --------------------------------------------------
# 2. 연도별 파일명 정의
# --------------------------------------------------
file_map = {
    2020: "p20.csv",
    2021: "p21.csv",
    2022: "p22.csv",
    2023: "p23.csv",
    2024: "p24.csv",
    2025: "p25.csv",
}

# --------------------------------------------------
# 3. 사용할 feature 변수 정의
# --------------------------------------------------
feature_vars = [
    "a03002",   # 스마트폰 구분
    "a03024",   # 음성 무제한 서비스 가입 여부
    "a03026",   # 데이터 무제한 서비스 가입 여부
    "c01002",   # 월평균 휴대폰 이용 총 금액(리코드)
    "c01004",   # 월평균 기기 할부금(리코드)
    "c02003",   # 휴대폰 결합상품 가입 여부
    "c02001",   # 휴대폰 요금 부담자
    "age1",     # 나이(만 연령)
    "income1",  # 개인 월평균 소득(연속형)
    "job1",     # 직업 유무
]

missing_codes = [9999, 9998, 9997]
year_dfs = []

# --------------------------------------------------
# 4. 문자열/숫자 정리용 함수
# --------------------------------------------------
def clean_numeric_series(series):
    """
    문자열 공백/NBSP 제거
    숫자형 변환
    KMP 결측 코드(9999, 9998, 9997) -> NaN 처리
    """
    series = series.astype(str).str.replace("\xa0", "", regex=False).str.strip()
    series = series.replace(["", "nan", "None"], np.nan)
    series = pd.to_numeric(series, errors="coerce")
    series = series.replace(missing_codes, np.nan)
    return series

def clean_pid_series(series):
    """
    pid는 식별자이므로 문자열 기준으로 정리
    """
    series = series.astype(str).str.replace("\xa0", "", regex=False).str.strip()
    series = series.replace(["", "nan", "None"], np.nan)
    return series

# --------------------------------------------------
# 5. 연도별 CSV 불러오기
# --------------------------------------------------
for year, file_name in file_map.items():
    file_path = os.path.join(raw_dir, file_name)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"파일이 없습니다: {file_path}")

    print(f"\n[{year}] 파일 불러오는 중: {file_path}")

    df = pd.read_csv(file_path, low_memory=False, encoding="cp949")

    yy = str(year)[-2:]
    pid_col = "pid"
    telco_col = f"p{yy}a03008"
    feature_cols = [f"p{yy}{var}" for var in feature_vars]

    expected_cols = [pid_col, telco_col] + feature_cols
    use_cols = [col for col in expected_cols if col in df.columns]
    missing_cols = [col for col in expected_cols if col not in df.columns]

    print(f"[{year}] 사용할 컬럼 수: {len(use_cols)}")

    if missing_cols:
        print(f"[{year}] 누락 컬럼: {missing_cols}")

    if pid_col not in df.columns:
        raise ValueError(f"{year}년 파일에 pid 컬럼이 없습니다.")

    if telco_col not in df.columns:
        raise ValueError(f"{year}년 파일에 통신사 컬럼({telco_col})이 없습니다.")

    df = df[use_cols].copy()

    # --------------------------------------------------
    # 6. pid 정리
    # --------------------------------------------------
    df[pid_col] = clean_pid_series(df[pid_col])

    # pid 결측 제거
    df = df[df[pid_col].notna()].copy()

    # --------------------------------------------------
    # 7. 숫자형 컬럼 정리
    # --------------------------------------------------
    df[telco_col] = clean_numeric_series(df[telco_col])

    for col in feature_cols:
        if col in df.columns:
            df[col] = clean_numeric_series(df[col])

    # 통신사 유효값만 남기기: 1=SKT, 2=KT, 3=LGU+, 4=MVNO
    df[telco_col] = df[telco_col].where(df[telco_col].isin([1, 2, 3, 4]), np.nan)

    # --------------------------------------------------
    # 8. 컬럼명 통일
    # --------------------------------------------------
    rename_dict = {
        pid_col: "pid",
        telco_col: "telco",
    }

    for var in feature_vars:
        old_col = f"p{yy}{var}"
        new_col = f"{var}_tminus1"
        if old_col in df.columns:
            rename_dict[old_col] = new_col

    df = df.rename(columns=rename_dict)

    # --------------------------------------------------
    # 9. 이진 변수 1/0 변환
    # --------------------------------------------------
    if "a03024_tminus1" in df.columns:
        df["a03024_tminus1"] = df["a03024_tminus1"].map({1: 1, 2: 0})

    if "a03026_tminus1" in df.columns:
        df["a03026_tminus1"] = df["a03026_tminus1"].map({1: 1, 2: 0})

    if "c02003_tminus1" in df.columns:
        df["c02003_tminus1"] = df["c02003_tminus1"].map({1: 1, 2: 0})

    if "job1_tminus1" in df.columns:
        df["job1_tminus1"] = df["job1_tminus1"].map({1: 1, 2: 0})

    # 연도 정보 추가
    df["year"] = year

    # --------------------------------------------------
    # 10. pid 중복 확인 및 제거
    # --------------------------------------------------
    dup_count = df.duplicated(subset=["pid"]).sum()
    if dup_count > 0:
        print(f"[{year}] pid 중복 {dup_count}건 발견 -> 첫 번째 값만 유지")
        df = df.drop_duplicates(subset=["pid"], keep="first").copy()

    print(f"[{year}] 정리 후 shape: {df.shape}")

    year_dfs.append(df)

# --------------------------------------------------
# 11. 전환(transition) 데이터 생성
# --------------------------------------------------
transition_list = []

for i in range(len(year_dfs) - 1):
    df_t0 = year_dfs[i].copy()
    df_t1 = year_dfs[i + 1].copy()

    year_t0 = df_t0["year"].iloc[0]
    year_t1 = df_t1["year"].iloc[0]

    print(f"\n[전환 생성] {year_t0} -> {year_t1}")

    # t-1 시점 통신사
    df_t0 = df_t0.rename(columns={"telco": "telco_t0"})

    # t 시점에서는 통신사만 사용
    df_t1 = df_t1[["pid", "telco"]].rename(columns={"telco": "telco_t1"})

    merged = pd.merge(df_t0, df_t1, on="pid", how="inner")

    print(f"[{year_t0}->{year_t1}] merge 후 shape: {merged.shape}")

    merged = merged[
        merged["telco_t0"].isin([1, 2, 3, 4]) &
        merged["telco_t1"].isin([1, 2, 3, 4])
    ].copy()

    print(f"[{year_t0}->{year_t1}] 유효 통신사 필터 후 shape: {merged.shape}")

    # 라벨 생성
    merged["churn_any"] = (merged["telco_t0"] != merged["telco_t1"]).astype(int)

    merged["churn_to_mvno"] = (
        merged["telco_t0"].isin([1, 2, 3]) &
        (merged["telco_t1"] == 4)
    ).astype(int)

    merged["year_t0"] = year_t0
    merged["year_t1"] = year_t1

    transition_list.append(merged)

# --------------------------------------------------
# 12. 전환 데이터 합치기
# --------------------------------------------------
if len(transition_list) == 0:
    raise ValueError("전환 데이터가 생성되지 않았습니다. pid 매칭 여부를 확인하세요.")

train_df = pd.concat(transition_list, ignore_index=True)

# 같은 pid가 같은 전환 구간에 중복되면 제거
train_df = train_df.drop_duplicates(subset=["pid", "year_t0", "year_t1"]).copy()

# --------------------------------------------------
# 13. 최종 컬럼 순서 정리
# --------------------------------------------------
final_cols = [
    "pid",
    "year_t0",
    "year_t1",
    "telco_t0",
    "telco_t1",
    "churn_any",
    "churn_to_mvno",
    "a03002_tminus1",
    "a03024_tminus1",
    "a03026_tminus1",
    "c01002_tminus1",
    "c01004_tminus1",
    "c02003_tminus1",
    "c02001_tminus1",
    "age1_tminus1",
    "income1_tminus1",
    "job1_tminus1",
]

final_cols = [col for col in final_cols if col in train_df.columns]
train_df = train_df[final_cols].copy()

train_df = train_df.sort_values(["pid", "year_t0", "year_t1"]).reset_index(drop=True)

# --------------------------------------------------
# 14. 최소 검증 출력
# --------------------------------------------------
print("\n" + "=" * 60)
print("최종 train_df 정보")
print("=" * 60)

print("최종 shape:", train_df.shape)

print("\n컬럼 목록")
print(train_df.columns.tolist())

print("\nchurn_any 분포")
print(train_df["churn_any"].value_counts(dropna=False).sort_index())

print("\nchurn_to_mvno 분포")
print(train_df["churn_to_mvno"].value_counts(dropna=False).sort_index())

print("\n컬럼별 결측률")
print(train_df.isna().mean().sort_values(ascending=False))

print("\n추가 컬럼 기초통계")
extra_cols = [col for col in ["age1_tminus1", "income1_tminus1", "job1_tminus1"] if col in train_df.columns]
print(train_df[extra_cols].describe(include="all"))

print("\n상위 5행")
print(train_df.head())

# --------------------------------------------------
# 15. 파일 저장
# --------------------------------------------------
csv_path = os.path.join(processed_dir, "train_df_2020_2025.csv")

train_df.to_csv(csv_path, index=False, encoding="utf-8-sig")

print("\n저장 완료")
print(csv_path)