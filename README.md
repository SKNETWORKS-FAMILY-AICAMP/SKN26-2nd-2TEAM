## 데이터 설명

### 사용 데이터
- 한국미디어패널(KMP) 2020~2025 개인조사 CSV (`p20 ~ p25`)
- 코드북 `P_codebook_v32.xlsx`

### 데이터 구성 방식
원천 데이터는 `pid` 기준으로 전년(`t-1`)과 다음 해(`t`)를 연결하여 transition 기반 long panel 형태로 재구성하였다.  
즉, 한 행은 한 개인의 `year_t0 → year_t1` 전환을 의미한다.

예시
- `2020 → 2021`
- `2021 → 2022`
- `2022 → 2023`
- `2023 → 2024`
- `2024 → 2025`

최종 데이터셋은 총 `41,299행`, `17컬럼`으로 구성하였다.

### 원본 데이터 안내
- 원본 KMP CSV 파일은 용량 문제로 본 저장소에는 포함하지 않았다.
- 따라서 `data/raw/` 폴더는 비워두었거나 업로드하지 않은 상태이며, 전처리 및 분석은 별도로 확보한 원본 데이터 기준으로 진행하였다.


---

## 전처리 방법

전처리 파이프라인에서는 아래 기준을 적용하였다.

- 결측 코드 `9999`, `9998`, `9997`를 `NaN`으로 변환
- 문자열 공백 및 NBSP 제거
- 통신사 변수는 유효값 `{1, 2, 3, 4}`만 유지
- 일부 이진 변수는 `1/2 → 1/0`으로 변환
- `pid`, `year_t0`, `year_t1` 기준 중복 제거
- 예측 입력에는 항상 `t-1` 시점 변수만 사용
- `telco` 관련 직접 정보는 입력 변수에서 제외하여 데이터 누수를 방지

또한 기존 통신 이용 특성 변수에 더해 아래 개인 특성 변수를 추가 반영하였다.

- `age1`: 나이(만 연령)
- `income1`: 개인 월평균 소득
- `job1`: 직업 유무

이를 통해 통신 이용 특성뿐 아니라 개인의 생애주기와 경제적 배경까지 함께 반영하는 분석 구조를 구성하였다.

---

## 데이터 구조 및 라벨 분포

EDA 및 전처리 점검 결과, 라벨 분포는 다음과 같았다.

- `churn_any`: `14,982 / 41,299 ≈ 36.3%`
- `churn_to_mvno`: `515 / 41,299 ≈ 1.25%`

이를 통해 다음을 확인할 수 있었다.

- `churn_any`는 비교적 표본이 충분한 문제
- `churn_to_mvno`는 매우 희소한 이벤트로 클래스 불균형이 매우 큰 문제
- 따라서 두 문제는 같은 기준으로 해석하면 안 되며, 서로 다른 평가 관점이 필요함



---

## 분석 흐름

프로젝트는 아래 순서로 진행하였다.

### 1. `00_eda_overview.ipynb`
- 데이터 기본 구조 확인
- 라벨 분포 확인
- 주요 변수 분포 및 기초 관계 확인

### 2. `01_preprocessing_check.ipynb`
- 전처리 결과 점검
- 전환형 구조 확인
- 추가 변수(`age1`, `income1`, `job1`) 반영 여부 검증

### 3. `02_churn_any_baseline.ipynb`
- `churn_any` 단일 hold-out baseline 모델 비교

### 4. `03_churn_to_mvno_baseline.ipynb`
- `churn_to_mvno` baseline 모델 비교
- threshold 조정 및 불균형 대응 기법 확인

### 5. `04_churn_any_cv_tuning.ipynb`
- `GroupKFold` 기반 `churn_any` 교차검증
- `RandomForest` 하이퍼파라미터 튜닝
- threshold 비교 및 해석

### 6. `05_final_summary.ipynb`
- 전체 프로젝트 결과 요약
- 문제별 핵심 결론 및 한계 정리

---

## 1. churn_any 분석 결과

`churn_any`는 일반적인 통신사 변경 여부를 예측하는 문제로, hold-out baseline 비교와 GroupKFold 기반 교차검증·튜닝을 함께 진행하였다.

### hold-out baseline 결과
- `DecisionTree`: Recall `0.8646`, F1 `0.5265`
- `LogisticRegression`: Recall `0.5588`, F1 `0.4534`
- `RandomForest`: Recall `0.4794`, F1 `0.4427`

해석하면,
- `DecisionTree`는 실제 이탈자를 최대한 놓치지 않는 강한 탐지형 baseline
- `LogisticRegression`은 중간형 기준선 역할
- `RandomForest`는 상대적으로 더 보수적이지만 안정적인 대안

또한 `GradientBoosting`, `XGBoost`는 Accuracy는 높게 보일 수 있었지만 Recall이 매우 낮아 실제 churn 탐지 관점에서는 실용성이 떨어졌다.

### GroupKFold baseline 결과
GroupKFold 평균 기준에서는 `DecisionTree`가 baseline 최고 성능을 보였다.

- `DecisionTree`: Recall `0.8244`, F1 `0.5266`
- `LogisticRegression`: Recall `0.5795`, F1 `0.4692`
- `RandomForest`: Recall `0.5230`, F1 `0.4608`



### RandomForest 튜닝 결과
최적 조합은 다음과 같았다.

- `n_estimators = 300`
- `max_depth = 8`
- `min_samples_split = 10`
- `min_samples_leaf = 3`

튜닝 결과, `RandomForest`는 baseline 대비 분명한 개선을 보였다.

- F1: `0.4608 → 0.5187`
- Recall: `0.5230 → 0.7262`

또한 hold-out 기준 threshold 비교에서는 `0.45`에서 가장 좋은 균형을 보였다.

- Precision: `0.3819`
- Recall: `0.8868`
- F1: `0.5339`



### churn_any 해석
`churn_any`는 단말 특성, 통신 이용 특성, 비용 부담, 소득, 나이/연령대가 함께 작용하는 문제로 해석할 수 있었다.

최종 정리는 다음과 같다.

- hold-out baseline 최고 성능: `DecisionTree`
- GroupKFold baseline 최고 성능: `DecisionTree`
- 튜닝 후 실사용 후보: `RandomForest`

---

## 2. churn_to_mvno 분석 결과

`churn_to_mvno`는 전체 데이터 기준 양성 비율이 약 `1.25%`에 불과한 매우 희소한 문제였다.  
특히 hold-out test split 기준 양성 비율은 약 `1.01%` 수준으로, 극심한 클래스 불균형이 핵심 난점이었다.

### baseline 결과
- `LogisticRegression`: Recall `0.5476`, F1 `0.0277`, ROC-AUC `0.6145`, PR-AUC `0.0189`
- `DecisionTree`: Recall `0.5357`, F1 `0.0276`, ROC-AUC `0.5923`, PR-AUC `0.0134`
- `RandomForest`: Recall `0.0238`, F1 `0.0191`
- `GradientBoosting`, `XGBoost`: 양성 탐지 거의 불가

해석하면,
- `LogisticRegression`이 가장 안정적인 기준선 역할
- `DecisionTree`는 유사한 탐지형 대안
- `RandomForest`, `GradientBoosting`, `XGBoost`는 기본 설정 기준으로 실제 양성 탐지력이 매우 약함

### threshold 조정 결과
`LogisticRegression`에서 F1 기준 최적 threshold를 찾았을 때도 최고 F1은 `0.0402` 수준에 머물렀다.  
즉, threshold 조정만으로는 희소 클래스 문제의 근본적인 한계를 넘기 어려웠다.

### EasyEnsemble 결과
불균형 대응 기법인 `EasyEnsemble`도 추가 실험으로 적용하였다.

- Recall `0.5952`
- F1 `0.0313`

일부 보완 가능성은 보였지만, Precision과 전체 실용성 측면에서는 여전히 한계가 컸다.



### churn_to_mvno 해석
`churn_to_mvno`는 단순히 모델을 바꾸거나 threshold를 조정한다고 해결되는 문제가 아니라,  
극심한 클래스 불균형과 변수 정보의 한계가 동시에 존재하는 문제였다.

따라서 이 과제는 성능 자체보다도 데이터 구조의 한계를 파악하고, 향후 추가 변수와 불균형 대응 전략이 필요함을 확인했다는 점에서 의미가 있다.

---

## 공통 인사이트

두 문제를 함께 보면 공통적으로 비용 및 이용 특성이 중요한 축으로 작용하였다.  
특히 아래 변수들이 반복적으로 중요한 신호로 나타났다.

- 스마트폰 구분
- 월평균 휴대폰 이용 총 금액
- 월평균 기기 할부금
- 나이/연령대
- 개인 월평균 소득

즉 고객 이탈은 단순한 통신 이용 행태만으로 설명되지 않고,  
비용 관련 변수, 단말 및 이용 특성, 개인 배경 특성이 함께 작용하는 문제임을 확인할 수 있었다.


---

## 한계 및 향후 개선 방향

이번 프로젝트는 `t-1` 시점의 상태값을 바탕으로 통신사 이탈을 예측했다는 점에서 의미가 있었지만,  
특히 `churn_to_mvno`처럼 희소한 문제에서는 변수 정보와 라벨 구조의 한계도 함께 확인할 수 있었다.  
향후에는 아래 방향으로 확장하면 분석의 실효성을 더 높일 수 있다.

1. 변화량 중심 변수 확장  
현재는 `t-1` 시점의 상태값을 주로 사용했지만, 실제 이탈은 절대 수준보다 변화 폭에 더 민감할 수 있다.  
따라서 월평균 휴대폰 이용 금액 변화, 기기 할부금 변화, 서비스 가입 여부 변화처럼 `t-1 → t` 직전의 변화량 변수를 추가하면 이탈 신호를 더 잘 포착할 수 있다.

2. MVNO 이동에 특화된 추가 변수 확보  
`churn_to_mvno`는 단순 통신사 변경보다 훨씬 희소하고 구조적으로 어려운 문제였다.  
향후에는 약정 만료 여부, 요금제 변경 이력, 단말 교체 주기, 결합상품 유지 여부처럼 MVNO 이동과 직접적으로 연결될 수 있는 변수를 추가해 문제 자체의 설명력을 높일 필요가 있다.

3. 희소 라벨 대응 전략 고도화  
`churn_to_mvno`에서는 threshold 조정만으로는 한계가 분명했다.  
따라서 향후에는 class weight 조정, resampling, 불균형 특화 앙상블, 비용 민감 학습처럼 희소 클래스 대응 전략을 보다 체계적으로 비교할 필요가 있다.

4. 시간 일반화 성능 검증  
현재 분석은 transition 구조를 잘 반영했지만, 실제 활용 가능성을 보려면 특정 연도에서 학습하고 다음 연도로 평가하는 방식의 시간 기반 검증도 함께 필요하다.  
이를 통해 모델이 단순히 현재 데이터에 맞는지, 아니면 이후 시점에도 일반화되는지를 더 명확하게 확인할 수 있다.
