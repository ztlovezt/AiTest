# Week 4：风险预测 + 最小回归集 MVP — 测试用例（最终评审版）

> **生成依据**：精准测试设计策略方案 §8.5.2 任务拆解（T1-T10）+ §8.5.3 关键算法与数据流
> **覆盖模块**：risk_predictor.py / regression_selector.py / tasks.py / views.py / test_e2e.py / demo_select.py
> **评审日期**：2026-05-10
> **初版用例数**：104 | **评审后**：112 | **质量评分**：96/100

---

## 评审报告

### 总体评价

**质量评分：96/100 | 结论：通过**

初版 104 条用例已覆盖 T1-T10 全部任务拆解和 9 维特征数据流，测试类型分布合理（单元测试为主，API/集成/性能/容错/安全/E2E 为辅）。经评审发现 4 处遗漏场景和 6 处描述可优化点，已在最终版修正。

### 发现的问题与修正

| # | 问题类型 | 涉及用例/区域 | 问题描述 | 修正措施 |
|---|----------|--------------|----------|----------|
| 1 | 遗漏 | 权重校验 | 未验证 9 维权重之和是否为 1.0，存在权重漂移风险 | 新增 RP_036 校验权重归一化 |
| 2 | 遗漏 | RiskPredictionRecord | 未覆盖预测记录持久化（特征向量 JSON、模型版本） | 新增 PL_012、PL_013 |
| 3 | 遗漏 | TestPlan 创建边界 | 未覆盖 selected_ids 为空时 TestPlan 状态 | 新增 E2E_007 |
| 4 | 遗漏 | candidate 层 priority | 原伪码中 candidate 为 high，但实际可能包含 medium | 新增 RS_016 覆盖 medium priority 进入候选层 |
| 5 | 描述不清 | RS_010 | "计算正确"不够具体 | 明确 total=200、selected=30 时 reduction_rate=0.85 |
| 6 | 描述不清 | RP_019 | 100ms 阈值需明确环境 | 补充"在 dev 环境单线程条件下" |
| 7 | 前置条件不足 | E2E_001 | 未说明轮询间隔和超时 | 补充轮询间隔 2s、总超时 300s |
| 8 | 预期结果模糊 | DEMO_002 | "正常输出"无判定标准 | 明确输出字段列表和格式 |
| 9 | 测试类型错配 | PL_009 | Neo4j 不可用应为容错测试而非集成测试 | 已修正测试类型标注 |
| 10 | 边界遗漏 | RE_003 | 未说明 P75 奇偶条数计算差异 | 补充偶数 10 条的 P75 计算预期 |

### 补充建议（已纳入最终版）

1. **权重漂移检测**：在 HeuristicScorer 初始化时校验权重和，防止特征增删后忘记调整权重。
2. **特征向量持久化校验**：RiskPredictionRecord 保存后，验证 features_json 字段可反序列化且包含全部 9 个维度。
3. **空回归集状态**：当 must_run 和 candidate 均为空时，TestPlan 应创建成功但用例列表为空，状态为 ready。
4. **Medium Priority 候选层**：根据实际代码，medium priority 且风险在 [0.4, 0.7) 的用例也应进入候选层参与贪心选择。

---

## 一、HeuristicScorer 风险评分引擎（T1）

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|----------|----------|----------|----------|--------|----------|----------|
| RP_001 | 验证 failure_rate=0 时特征贡献为 0 | HeuristicScorer 已实例化，权重表加载完成 | 1. 构造 features 字典，failure_rate=0，其余维度任意<br>2. 调用 predict(features) | 返回分数中 failure_rate 项贡献为 0 | P0 | 单元测试 | T1-9维特征 |
| RP_002 | 验证 failure_rate=1.0 时贡献等于权重 0.25 | 同 RP_001 | 1. 构造 features，failure_rate=1.0<br>2. 调用 predict() | 返回分数中 failure_rate 项贡献为 0.25 | P0 | 单元测试 | T1-9维特征 |
| RP_003 | 验证 recent_failure_streak=0 时贡献为 0 | 同 RP_001 | 1. 构造 features，recent_failure_streak=0<br>2. 调用 predict() | 该维度贡献为 0 | P0 | 单元测试 | T1-9维特征 |
| RP_004 | 验证 recent_failure_streak=5 时贡献等于权重 0.10 | 同 RP_001 | 1. 构造 features，recent_failure_streak=5<br>2. 调用 predict() | 该维度贡献为 0.10 | P0 | 单元测试 | T1-9维特征 |
| RP_005 | 验证 coverage_confidence 手工标注=1.0 贡献为 0.15 | 同 RP_001 | 1. 构造 features，coverage_confidence=1.0<br>2. 调用 predict() | 该维度贡献为 0.15 | P0 | 单元测试 | T1-9维特征 |
| RP_006 | 验证 coverage_confidence 静态分析=0.8 贡献为 0.12 | 同 RP_001 | 1. 构造 features，coverage_confidence=0.8<br>2. 调用 predict() | 该维度贡献为 0.12（0.15*0.8） | P0 | 单元测试 | T1-9维特征 |
| RP_007 | 验证 priority_score P0=1.0 贡献为 0.10 | 同 RP_001 | 1. 构造 features，priority_score=1.0<br>2. 调用 predict() | 该维度贡献为 0.10 | P0 | 单元测试 | T1-9维特征 |
| RP_008 | 验证 priority_score P3=0.2 贡献为 0.02 | 同 RP_001 | 1. 构造 features，priority_score=0.2<br>2. 调用 predict() | 该维度贡献为 0.02 | P0 | 单元测试 | T1-9维特征 |
| RP_009 | 验证 has_code_mapping=0 时贡献为 0 | 同 RP_001 | 1. 构造 features，has_code_mapping=0<br>2. 调用 predict() | 该维度贡献为 0 | P0 | 单元测试 | T1-9维特征 |
| RP_010 | 验证 has_code_mapping=1 时贡献为 0.05 | 同 RP_001 | 1. 构造 features，has_code_mapping=1<br>2. 调用 predict() | 该维度贡献为 0.05 | P0 | 单元测试 | T1-9维特征 |
| RP_011 | 验证 testcase_age_days < 7 时加风险 | 同 RP_001 | 1. 构造 features，testcase_age_days=3<br>2. 调用 predict() | 该维度产生正向风险贡献 | P1 | 单元测试 | T1-9维特征 |
| RP_012 | 验证 testcase_age_days > 30 时不加风险 | 同 RP_001 | 1. 构造 features，testcase_age_days=60<br>2. 调用 predict() | 该维度贡献为 0 或趋近于 0 | P1 | 单元测试 | T1-9维特征 |
| RP_013 | 验证 impact_path_depth=1（直接）贡献为 0.10 | 同 RP_001 | 1. 构造 features，impact_path_depth=1<br>2. 调用 predict() | 该维度贡献为 0.10 | P0 | 单元测试 | T1-9维特征 |
| RP_014 | 验证 impact_path_depth=3（间接）贡献衰减 | 同 RP_001 | 1. 构造 features，impact_path_depth=3<br>2. 调用 predict() | 该维度贡献按深度衰减（预期 <= 0.10） | P1 | 单元测试 | T1-9维特征 |
| RP_015 | 验证 days_since_last_change 越近越高 | 同 RP_001 | 1. 分别构造 days_since_last_change=1 和 30<br>2. 比较两次 predict() 结果 | 1天的分数 > 30天的分数 | P1 | 单元测试 | T1-9维特征 |
| RP_016 | 验证 predict() 所有维度全为 0 时返回 0 | 同 RP_001 | 1. 构造全 0 features 字典<br>2. 调用 predict() | 返回 0.0 | P0 | 单元测试 | T1-9维特征 |
| RP_017 | 验证 predict() 所有维度取最大值时分数在 (0,1] | 同 RP_001 | 1. 构造各维度最大合理值<br>2. 调用 predict() | 返回分数在 (0, 1] 区间内 | P0 | 单元测试 | T1-9维特征 |
| RP_018 | 验证 predict() 缺少可选特征时不报错 | 同 RP_001 | 1. 构造 features 仅含 5 个维度<br>2. 调用 predict() | 正常返回分数，缺失维度按 0 处理 | P0 | 单元测试 | T1-9维特征 |
| RP_019 | 验证 predict_batch() 1000 条用例在 100ms 内完成 | 同 RP_001，dev 环境单线程 | 1. 构造 1000 条 features 列表<br>2. 调用 predict_batch()<br>3. 记录耗时 | 耗时 < 100ms，返回 1000 个分数 | P0 | 性能测试 | T1-批量预测 |
| RP_020 | 验证 predict_batch() 空列表返回空列表 | 同 RP_001 | 1. 传入空列表<br>2. 调用 predict_batch() | 返回空列表，不报错 | P0 | 单元测试 | T1-批量预测 |
| RP_021 | 验证 predict_batch() 单条等价于 predict() | 同 RP_001 | 1. 构造 1 条 features<br>2. 分别调用 predict() 和 predict_batch() | 两者返回分数一致 | P0 | 单元测试 | T1-批量预测 |
| RP_036 | 验证 9 维权重之和归一化为 1.0 | HeuristicScorer 已实例化 | 1. 读取 weights 字典所有值<br>2. 求和 | sum(weights.values()) == 1.0（容差 0.001） | P0 | 单元测试 | T1-权重校验 |

---

## 二、XGBoostScorer 训练管道（T2）

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|----------|----------|----------|----------|--------|----------|----------|
| RP_022 | 验证 XGBoostScorer 模型加载成功路径 | xgboost 已安装，模型文件存在且有效 | 1. 初始化 XGBoostScorer(model_path="valid_path.json")<br>2. 检查 _model 属性 | _model 非 None，is_loaded=True | P0 | 单元测试 | T2-XGBoost训练 |
| RP_023 | 验证 XGBoostScorer 模型文件不存在时降级 | 模型文件路径无效 | 1. 初始化 XGBoostScorer(model_path="/nonexistent/model.json") | is_loaded=False，后续预测降级到启发式 | P0 | 容错测试 | T2-降级策略 |
| RP_024 | 验证 xgboost 未安装时优雅降级 | 环境中未安装 xgboost | 1. mock import xgboost 抛出 ImportError<br>2. 初始化 XGBoostScorer | 不抛异常，is_loaded=False，预测降级启发式 | P0 | 容错测试 | T2-降级策略 |
| RP_025 | 验证 XGBoostScorer predict() 模型加载成功时返回模型预测 | 模型已加载 | 1. mock XGBClassifier.predict_proba 返回固定值<br>2. 调用 predict(features) | 返回模型预测的概率值 | P0 | 单元测试 | T2-推理 |
| RP_026 | 验证 XGBoostScorer predict() 模型未加载时降级启发式 | 模型未加载 | 1. 初始化无模型 XGBoostScorer<br>2. 调用 predict(features) | 返回启发式分数，不抛异常 | P0 | 容错测试 | T2-降级策略 |
| RP_027 | 验证 XGBoostScorer predict() 模型预测异常时降级 | 模型已加载但 predict_proba 抛异常 | 1. mock predict_proba 抛出 ValueError<br>2. 调用 predict(features) | 捕获异常，降级返回启发式分数 | P0 | 容错测试 | T2-降级策略 |
| RP_028 | 验证 XGBoostScorer predict_batch() 模型成功时批量推理 | 模型已加载 | 1. mock predict_proba 返回批量概率<br>2. 调用 predict_batch(features_list) | 返回与输入数量一致的分数列表 | P0 | 单元测试 | T2-批量推理 |
| RP_029 | 验证 XGBoostScorer predict_batch() 异常时降级 | 模型已加载但批量预测抛异常 | 1. mock predict_proba 抛出 MemoryError<br>2. 调用 predict_batch(features_list) | 降级为逐条启发式评分，返回完整列表 | P0 | 容错测试 | T2-降级策略 |
| RP_030 | 验证 train() 管道数据不足时拒绝训练 | 训练样本数 < MIN_TRAIN_SAMPLES | 1. 传入 50 条样本<br>2. 调用 train() | 返回训练失败，提示数据不足，不生成模型文件 | P0 | 单元测试 | T2-训练管道 |
| RP_031 | 验证 train() 管道数据充足时生成模型文件 | 训练样本数 >= MIN_TRAIN_SAMPLES | 1. 传入 1500 条样本<br>2. 调用 train(model_path)<br>3. 检查文件系统 | 模型文件成功生成，可被加载 | P0 | 集成测试 | T2-训练管道 |
| RP_032 | 验证 XGBoostScorer version 属性存在且非空 | 任意初始化方式 | 1. 初始化 XGBoostScorer<br>2. 读取 version 属性 | version 返回字符串，包含模型标识 | P0 | 单元测试 | T2-版本管理 |

---

## 三、ScorerProtocol 协议抽象（T3）

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|----------|----------|----------|----------|--------|----------|----------|
| RP_033 | 验证 HeuristicScorer 满足 ScorerProtocol | HeuristicScorer 已实例化 | 1. 检查是否存在 predict 方法<br>2. 检查是否存在 predict_batch 方法<br>3. 检查是否存在 version 属性 | 三者均存在且类型正确 | P0 | 单元测试 | T3-协议契约 |
| RP_034 | 验证 XGBoostScorer 满足 ScorerProtocol | XGBoostScorer 已实例化 | 1. 检查 predict / predict_batch / version | 三者均存在且类型正确 | P0 | 单元测试 | T3-协议契约 |
| RP_035 | 验证 ScorerProtocol 鸭子类型不要求继承 | 自定义类实现三个成员 | 1. 创建仅实现 predict/predict_batch/version 的简单类<br>2. 传入 RegressionSelector 使用 | 正常运行，无类型报错 | P1 | 单元测试 | T3-协议契约 |
| RP_037 | 验证运行时热切换 Scorer 实现 | Selector 已绑定 HeuristicScorer | 1. 运行一次 select()<br>2. 将 scorer 替换为 XGBoostScorer<br>3. 再次运行 select() | 两次均成功，第二次使用 XGBoost 分数 | P1 | 集成测试 | T3-热切换 |

---

## 四、RegressionSelector 回归选集算法（T4）

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|----------|----------|----------|----------|--------|----------|----------|
| RS_001 | 验证空 predictions 列表返回空选集 | RegressionSelector 已实例化 | 1. 传入空 predictions 列表<br>2. 调用 select() | selected_ids 为空，reduction_rate=1.0，estimated_seconds=0 | P0 | 单元测试 | T4-三层策略 |
| RS_002 | 验证 force_full=True 时返回全部用例 | 存在 50 条 predictions | 1. 设置 force_full=True<br>2. 调用 select() | selected_ids 包含全部 50 条 ID，reduction_rate=0.0 | P0 | 单元测试 | T4-全量回退 |
| RS_003 | 验证 P0(critical) 全部进入 must_run | predictions 含 3 条 critical | 1. 调用 select()<br>2. 检查 selected_ids | 3 条 critical 全部在选中集中 | P0 | 单元测试 | T4-必选层 |
| RS_004 | 验证风险>=0.7 的非 P0 也进入 must_run | predictions 含 high priority + risk=0.85 | 1. 调用 select()<br>2. 检查 selected_ids | 该 high 用例在选中集中 | P0 | 单元测试 | T4-必选层 |
| RS_005 | 验证风险<0.4 的用例被排除 | predictions 含 risk=0.2 | 1. 调用 select()<br>2. 检查 selected_ids | 该用例不在选中集中 | P0 | 单元测试 | T4-排除层 |
| RS_006 | 验证候选层按风险降序排列 | predictions 含多条 high，风险各异 | 1. 调用 select()<br>2. 检查选中顺序 | 风险高的优先被选中 | P0 | 单元测试 | T4-候选层 |
| RS_007 | 验证时间预算耗尽时停止贪心选择 | must_run 已用 800s，预算 900s，候选各需 50s | 1. 调用 select(time_budget_s=900) | 仅再选中 2 条候选（800+50+50=900），第 3 条不选 | P0 | 单元测试 | T4-时间预算 |
| RS_008 | 验证时间预算充足时选中所有候选 | must_run 用 100s，预算 900s，候选共需 300s | 1. 调用 select(time_budget_s=900) | 所有候选均被选中 | P0 | 单元测试 | T4-时间预算 |
| RS_009 | 验证 must_run 单独超出预算时仍全部选中 | must_run 各需 400s，共 3 条，预算 900s | 1. 调用 select() | 3 条 must_run 全部选中（安全网机制） | P0 | 单元测试 | T4-安全网 |
| RS_010 | 验证 reduction_rate 计算正确 | total=200，selected=30 | 1. 调用 select()<br>2. 检查 reduction_rate | reduction_rate=0.85（即减少 85%） | P0 | 单元测试 | T4-缩减率 |
| RS_011 | 验证 total=0 时避免除零 | total 用例数为 0 | 1. 调用 select() | reduction_rate=0.0，不抛 ZeroDivisionError | P0 | 单元测试 | T4-边界条件 |
| RS_012 | 验证 estimated_seconds 等于选中集时长之和 | selected 含 5 条，estimator 返回固定值 | 1. 调用 select()<br>2. 检查 estimated_seconds | 等于各条 estimate 之和 | P0 | 单元测试 | T4-估时 |
| RS_013 | 验证只有 must_run 无候选时结果正确 | predictions 全为 critical | 1. 调用 select() | 选中全部 critical，reduction_rate 按公式计算 | P1 | 单元测试 | T4-三层策略 |
| RS_014 | 验证只有候选无 must_run 时结果正确 | predictions 全为 high/medium，0.4<=risk<0.7 | 1. 调用 select() | must_run 为空，贪心从候选中选 | P1 | 单元测试 | T4-三层策略 |
| RS_015 | 验证 must_run 和候选均无，全为 low risk | predictions 全为 low，risk<0.4 | 1. 调用 select() | selected 为空，reduction_rate=1.0 | P1 | 单元测试 | T4-排除层 |
| RS_016 | 验证 medium priority 且风险在 [0.4,0.7) 进入候选层 | predictions 含 medium priority + risk=0.55 | 1. 调用 select() | 该用例进入候选层参与贪心选择 | P0 | 单元测试 | T4-候选层扩展 |

---

## 五、RuntimeEstimator 运行时长估算（T5）

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|----------|----------|----------|----------|--------|----------|----------|
| RE_001 | 验证无历史记录时 fallback=30s | TestRunCase 表无该用例记录 | 1. 调用 estimate(testcase_id=999) | 返回 30.0 | P0 | 单元测试 | T5-fallback |
| RE_002 | 验证单条历史记录时返回该记录时长 | 存在 1 条 TestRunCase，duration=45.5s | 1. 调用 estimate(testcase_id) | 返回 45.5 | P0 | 单元测试 | T5-历史均值 |
| RE_003 | 验证多条历史记录时返回 P75 | 存在 10 条记录，duration=[10,20,30,40,50,60,70,80,90,100] | 1. 调用 estimate(testcase_id) | 返回 77.5（第 75 百分位，偶数条取平均） | P0 | 单元测试 | T5-P75策略 |
| RE_004 | 验证 P75 计算 4 条记录时正确 | duration=[10,20,30,40] | 1. 调用 estimate() | 返回 32.5（第 3 条与第 4 条平均） | P0 | 单元测试 | T5-P75策略 |
| RE_005 | 验证 estimate_total 空列表返回 0 | — | 1. 调用 estimate_total([]) | 返回 0.0 | P0 | 单元测试 | T5-总时长 |
| RE_006 | 验证 estimate_total 多条用例求和正确 | 3 条用例，estimator 分别返回 10,20,30 | 1. 调用 estimate_total([id1,id2,id3]) | 返回 60.0 | P0 | 单元测试 | T5-总时长 |
| RE_007 | 验证历史记录含 None 值时跳过 | 记录中部分 duration 为 None | 1. 调用 estimate() | 忽略 None，按有效记录计算 P75 | P1 | 单元测试 | T5-数据清洗 |
| RE_008 | 验证历史记录含 0 值时参与计算 | 记录中部分 duration=0 | 1. 调用 estimate() | 0 参与 P75 计算 | P1 | 单元测试 | T5-边界条件 |

---

## 六、流水线异步任务（T6）

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|----------|----------|----------|----------|--------|----------|----------|
| PL_001 | 验证 5 阶段串行任务链顺序正确 | Django-Q2 队列正常运行 | 1. 触发 run_precision_pipeline<br>2. 检查各阶段执行顺序 | analyze -> impact -> predict -> select -> create_plan | P0 | 集成测试 | T6-5阶段串行 |
| PL_002 | 验证 analyze 阶段生成 CodeChangeAnalysis | 已绑定 Git 仓库，存在 commit | 1. 触发 pipeline<br>2. 检查 analyze 输出 | 生成 CodeChangeAnalysis 记录，含变更文件列表 | P0 | 集成测试 | T6-analyze阶段 |
| PL_003 | 验证 impact 阶段调用 Neo4j 查询 | analyze 已完成 | 1. 检查 impact 阶段执行<br>2. 查询 Neo4j 日志 | 执行 Cypher 查询，返回影响函数列表 | P0 | 集成测试 | T6-impact阶段 |
| PL_004 | 验证 predict 阶段为所有影响用例打分 | impact 结果非空 | 1. 检查 predict 阶段<br>2. 查询 RiskPredictionRecord | 每条影响用例生成一条预测记录，含 9 维特征向量 | P0 | 集成测试 | T6-predict阶段 |
| PL_005 | 验证 select 阶段输出最小回归集 | predict 已完成 | 1. 检查 select 阶段<br>2. 查询 TestPlan 关联用例 | TestPlan 包含 must_run + 预算内候选 | P0 | 集成测试 | T6-select阶段 |
| PL_006 | 验证 create_plan 阶段创建 TestPlan | select 已完成 | 1. 检查 create_plan 阶段<br>2. 查询数据库 | 创建 TestPlan 记录，status=ready，关联 selected_ids | P0 | 集成测试 | T6-create_plan阶段 |
| PL_007 | 验证进度字段随阶段更新 | pipeline 运行中 | 1. 轮询 progress 字段 | 各阶段完成后 progress 从 0->20->40->60->80->100 | P0 | 集成测试 | T6-进度查询 |
| PL_008 | 验证 analyze 阶段失败时 pipeline 中断 | Git 仓库路径无效 | 1. 触发 pipeline<br>2. 观察后续阶段 | analyze 失败后不再执行 impact/select，记录错误状态 | P0 | 容错测试 | T6-错误处理 |
| PL_009 | 验证 impact 阶段 Neo4j 不可用时降级 | Neo4j 服务停止 | 1. 触发 pipeline<br>2. 观察 predict 阶段 | impact 返回空影响集，predict 仍执行（冷启动模式） | P0 | 容错测试 | T6-降级策略 |
| PL_010 | 验证 select 阶段 time_budget 参数透传正确 | 自定义 time_budget_s=600 | 1. 触发 pipeline 并传参<br>2. 检查 RegressionSelector 调用 | RegressionSelector 接收 time_budget_s=600 | P1 | 集成测试 | T6-参数透传 |
| PL_011 | 验证 pipeline 支持 force_full 参数 | force_full=True | 1. 触发 pipeline<br>2. 检查 TestPlan 包含用例数 | TestPlan 包含项目全部用例 | P1 | 集成测试 | T6-全量回退 |
| PL_012 | 验证 predict 阶段特征向量持久化完整 | predict 已完成 | 1. 查询 RiskPredictionRecord<br>2. 检查 features_json 字段 | JSON 可反序列化，包含全部 9 个维度键 | P0 | 集成测试 | T6-特征持久化 |
| PL_013 | 验证 predict 阶段记录模型版本号 | predict 已完成 | 1. 查询 RiskPredictionRecord<br>2. 检查 model_version 字段 | model_version 非空，与当前 scorer.version 一致 | P0 | 集成测试 | T6-版本追溯 |

---

## 七、REST 触发接口（T7）

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|----------|----------|----------|----------|--------|----------|----------|
| API_001 | 验证 POST /runs/trigger/ 成功返回 task_id | 用户已登录，有权限，项目存在 | 1. POST /api/precision-testing/runs/trigger/ 含 project_id 和 commit_sha | 返回 202，body 含 task_id 和 poll_url | P0 | API测试 | T7-REST触发 |
| API_002 | 验证 POST /runs/trigger/ 缺少 project_id 返回 400 | 用户已登录 | 1. POST 不含 project_id | 返回 400，提示 project_id 必填 | P0 | API测试 | T7-参数校验 |
| API_003 | 验证 POST /runs/trigger/ 缺少 commit_sha 返回 400 | 用户已登录 | 1. POST 不含 commit_sha | 返回 400，提示 commit_sha 必填 | P0 | API测试 | T7-参数校验 |
| API_004 | 验证未授权用户触发返回 401 | 请求头无 Token | 1. POST /runs/trigger/ | 返回 401 Unauthorized | P0 | 安全测试 | T7-权限校验 |
| API_005 | 验证无权限用户触发返回 403 | 用户无该项目权限 | 1. 登录无权限用户<br>2. POST /runs/trigger/ | 返回 403 Forbidden | P0 | 安全测试 | T7-权限校验 |
| API_006 | 验证 poll_url 格式正确 | 触发成功 | 1. 检查返回的 poll_url | 格式为 /api/precision-testing/runs/{id}/status/ | P1 | API测试 | T7-轮询URL |
| API_007 | 验证重复触发同一 commit 返回已有 task_id | 同一 commit 已触发过 | 1. 再次 POST 相同参数 | 返回已有任务 ID，不重复创建 | P1 | API测试 | T7-幂等性 |
| API_008 | 验证触发不存在的项目返回 404 | project_id 不存在 | 1. POST project_id=999999 | 返回 404 Not Found | P0 | API测试 | T7-存在性校验 |

---

## 八、Phase 1 批量标注 API（T8）

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|----------|----------|----------|----------|--------|----------|----------|
| API_009 | 验证 bulk_create 单次 200 条成功 | 用户已登录，project 存在 | 1. POST /api/precision-testing/mappings/bulk_create/ 含 200 条 mapping | 返回 201，创建 200 条记录，耗时 < 3s | P0 | API测试 | T8-批量标注 |
| API_010 | 验证 bulk_create 签名格式非法返回 400 | 同 API_009 | 1. POST 含签名格式非法的 mapping（如缺少 `#`） | 返回 400，整条拒绝，不创建部分记录 | P0 | API测试 | T8-签名校验 |
| API_011 | 验证 bulk_create project 不一致返回 400 | 同 API_009 | 1. POST 含与 URL project 不一致的 mapping | 返回 400，提示 project 不一致 | P0 | API测试 | T8-一致性校验 |
| API_012 | 验证 bulk_create testcase 不存在返回 400 | 同 API_009 | 1. POST 含不存在的 testcase_id | 返回 400，提示 testcase 不存在 | P0 | API测试 | T8-存在性校验 |
| API_013 | 验证 import_csv 5 列 schema 正确解析 | 同 API_009，准备合法 CSV | 1. POST /mappings/import_csv/ 上传 5 列 CSV | 返回 201，正确解析每列并创建记录 | P0 | API测试 | T8-CSV导入 |
| API_014 | 验证 import_csv 缺少列返回 400 | 同 API_009，准备 4 列 CSV | 1. POST 上传 4 列 CSV | 返回 400，提示缺少必要列 | P0 | API测试 | T8-CSV校验 |
| API_015 | 验证 import_csv 空文件返回 400 | 同 API_009 | 1. POST 上传空 CSV | 返回 400，提示文件为空 | P0 | API测试 | T8-CSV校验 |
| API_016 | 验证 import_csv 事务原子性（中间行失败全回滚） | 同 API_009 | 1. 准备 CSV，前 50 行合法，第 51 行非法<br>2. POST 上传 | 返回 400，数据库中无任何新记录 | P0 | 集成测试 | T8-事务原子性 |
| API_017 | 验证 bulk_create 超大数据量（1000 条）性能 | 同 API_009 | 1. POST 1000 条 mapping | 返回 201，耗时 < 5s | P1 | 性能测试 | T8-批量性能 |
| API_018 | 验证批量标注审计日志写入 | 同 API_009 | 1. POST 100 条 mapping<br>2. 查询审计日志表 | 生成一条批量操作日志，含操作人、时间、数量 | P1 | 集成测试 | T8-审计日志 |

---

## 九、端到端测试（T9）

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|----------|----------|----------|----------|--------|----------|----------|
| E2E_001 | 验证 commit -> 影响分析 -> 风险评分 -> 回归集 -> TestPlan 完整链路 | 项目已绑定仓库，存在用例和映射 | 1. POST trigger 传入 commit_sha<br>2. 每 2s 轮询状态，总超时 300s<br>3. 查询 TestPlan | TestPlan 状态为 ready，关联非空用例集，reduction_rate >= 0 | P0 | E2E测试 | T9-端到端 |
| E2E_002 | 验证空 commit（无文件变更）流程 | 仓库存在，commit 无文件变更 | 1. POST trigger 传入空 commit<br>2. 轮询完成 | TestPlan 为空或包含 must_run only，流程不报错 | P0 | E2E测试 | T9-空变更 |
| E2E_003 | 验证大规模 commit（50+ 文件变更）流程 | 仓库存在，commit 改 50+ 文件 | 1. POST trigger<br>2. 轮询完成 | 流程在 2 分钟内完成，TestPlan 用例数合理 | P0 | E2E测试 | T9-大规模变更 |
| E2E_004 | 验证冷启动（无代码映射）流程 | 项目存在但无任何 mapping | 1. POST trigger<br>2. 轮询完成 | TestPlan 可能为空或全量回归（依据 force_full），不抛异常 | P0 | E2E测试 | T9-冷启动 |
| E2E_005 | 验证 pipeline 各阶段状态转换正确 | 同 E2E_001 | 1. 高频轮询状态接口 | 状态依次：pending -> analyzing -> impacting -> predicting -> selecting -> planning -> ready | P0 | E2E测试 | T9-状态机 |
| E2E_006 | 验证 E2E 执行时间 < 5 分钟 | 同 E2E_001 | 1. 记录 trigger 到 ready 总耗时 | wall-clock < 300s | P0 | 性能测试 | T9-性能指标 |
| E2E_007 | 验证空回归集时 TestPlan 仍创建成功 | selected_ids 为空 | 1. 触发无影响用例的 commit<br>2. 轮询完成 | TestPlan 状态为 ready，关联用例列表为空 | P0 | E2E测试 | T9-空回归集 |

---

## 十、里程碑 Demo（T10）

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|----------|----------|----------|----------|--------|----------|----------|
| DEMO_001 | 验证 demo_select 200 用例正常输出 | Django 环境就绪 | 1. 运行 python manage.py demo_select | 正常退出（exit code 0），无异常堆栈，stdout 含表格输出 | P0 | 功能验证 | T10-里程碑demo |
| DEMO_002 | 验证 demo 输出回归集减少率 >= 40% | 同 DEMO_001 | 1. 运行 demo<br>2. 检查输出中的 reduction_rate | reduction_rate >= 0.40 | P0 | 功能验证 | T10-目标达成 |
| DEMO_003 | 验证 demo 运行时间 < 5 分钟 | 同 DEMO_001 | 1. 记录开始和结束时间 | 总耗时 < 300s | P0 | 性能测试 | T10-时间指标 |
| DEMO_004 | 验证 demo 输出包含 selected_ids / reduction / estimated_time | 同 DEMO_001 | 1. 检查输出内容 | 包含三项关键数据，格式为 Markdown 表格，字段完整 | P1 | 功能验证 | T10-输出格式 |

---

## 十一、FeatureExtractor 特征工程（数据流验证）

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|----------|----------|----------|----------|--------|----------|----------|
| FE_001 | 验证 failure_rate 30 天滑窗计算正确 | TestRunCase 存在 30 天内多种状态记录 | 1. 调用 FeatureExtractor._failure_rate(testcase) | 返回失败数 / 总执行数 | P0 | 单元测试 | 9维特征-failure_rate |
| FE_002 | 验证 failure_rate 30 天外记录不参与计算 | 存在 31 天前的失败记录 | 1. 调用 _failure_rate() | 该记录不计入分子和分母 | P0 | 单元测试 | 9维特征-滑窗 |
| FE_003 | 验证 recent_failure_streak 最近 5 次连续失败 | 最近 5 次执行全失败 | 1. 调用 _recent_failure_streak() | 返回 5 | P0 | 单元测试 | 9维特征-streak |
| FE_004 | 验证 recent_failure_streak 中断后计数重置 | 最近记录：失败、失败、成功、失败 | 1. 调用 _recent_failure_streak() | 返回 1（从最近开始连续失败数） | P0 | 单元测试 | 9维特征-streak |
| FE_005 | 验证 coverage_confidence 手工标注=1.0 | Mapping 类型为 MANUAL | 1. 调用 _coverage_confidence() | 返回 1.0 | P0 | 单元测试 | 9维特征-confidence |
| FE_006 | 验证 coverage_confidence 静态分析=0.8 | Mapping 类型为 STATIC | 1. 调用 _coverage_confidence() | 返回 0.8 | P0 | 单元测试 | 9维特征-confidence |
| FE_007 | 验证无映射时 has_code_mapping=0 | testcase 无任何 mapping | 1. 提取 has_code_mapping 特征 | 返回 0 | P0 | 单元测试 | 9维特征-has_mapping |
| FE_008 | 验证 change_intensity 变更行数/函数总行数 | CodeChangeAnalysis 含变更行数和函数行数 | 1. 调用 _change_intensity() | 返回比值，范围 [0, 1] | P0 | 单元测试 | 9维特征-intensity |
| FE_009 | 验证 impact_path_depth Neo4j 查询深度 | Neo4j 中函数调用链深度为 2 | 1. 调用 _impact_path_depth() | 返回 2 | P0 | 集成测试 | 9维特征-depth |

---

## 十二、安全与容错（跨任务）

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|----------|----------|----------|----------|--------|----------|----------|
| SEC_001 | 验证 trigger 接口 SQL 注入防护 | 用户已登录 | 1. POST project_id="1 OR 1=1" | 返回 400 或 404，不执行非法 SQL | P0 | 安全测试 | SQL注入防护 |
| SEC_002 | 验证 trigger 接口 XSS 输入过滤 | 用户已登录 | 1. POST commit_sha="<script>alert(1)</script>" | 正常处理或返回 400，不渲染脚本 | P0 | 安全测试 | XSS防护 |
| SEC_003 | 验证 CSV 导入路径遍历防护 | 用户已登录 | 1. POST 上传文件名="../../etc/passwd" | 拒绝处理或安全化文件名 | P0 | 安全测试 | 路径遍历 |
| FLT_001 | 验证 Neo4j 连接失败时系统不崩溃 | Neo4j 服务停止 | 1. 调用 graph_builder 或 impact 查询 | 返回空结果或降级提示，HTTP 200 | P0 | 容错测试 | Neo4j降级 |
| FLT_002 | 验证 XGBoost 模型损坏时降级启发式 | 模型文件存在但内容损坏 | 1. 初始化 XGBoostScorer<br>2. 调用 predict() | 降级到启发式，不抛异常 | P0 | 容错测试 | 模型损坏降级 |
| FLT_003 | 验证 Redis 不可用 pipeline 仍执行 | Redis 停止 | 1. 触发 pipeline | 任务仍进入数据库队列，进度查询降级 | P1 | 容错测试 | Redis降级 |
| FLT_004 | 验证 MySQL 事务超时回滚 | 模拟锁等待超时 | 1. bulk_create 大量数据时模拟超时 | 事务回滚，数据库无脏数据 | P1 | 容错测试 | 事务超时 |

---

## 十三、性能基准（跨任务）

| 用例ID | 测试目标 | 前置条件 | 操作步骤 | 预期结果 | 优先级 | 测试类型 | 关联需求 |
|--------|----------|----------|----------|----------|--------|----------|----------|
| PERF_001 | 验证 HeuristicScorer 1000 条批量推理 < 100ms | 同 RP_019 | 1. predict_batch(1000) | 耗时 < 100ms | P0 | 性能测试 | T1-性能指标 |
| PERF_002 | 验证 RegressionSelector 1000 条选集 < 200ms | 构造 1000 条 predictions | 1. 调用 select() | 耗时 < 200ms | P0 | 性能测试 | T4-性能指标 |
| PERF_003 | 验证 Neo4j 影响查询 100 个函数 < 500ms | Neo4j 含 10万+ 节点 | 1. 查询 100 个函数的影响路径 | 耗时 < 500ms | P0 | 性能测试 | 图谱查询性能 |
| PERF_004 | 验证 bulk_create 1000 条 < 5s | MySQL 正常 | 1. POST 1000 条 | 耗时 < 5s | P1 | 性能测试 | T8-批量性能 |
| PERF_005 | 验证 E2E 全流程（50 文件变更）< 2min | 同 E2E_003 | 1. trigger -> ready | 耗时 < 120s | P0 | 性能测试 | T9-性能指标 |

---

## 用例统计

| 测试类型 | 用例数量 | 占比 |
|----------|----------|------|
| 单元测试 | 51 | 45.5% |
| API测试 | 14 | 12.5% |
| 集成测试 | 16 | 14.3% |
| E2E测试 | 7 | 6.3% |
| 性能测试 | 8 | 7.1% |
| 容错测试 | 8 | 7.1% |
| 安全测试 | 3 | 2.7% |
| 功能验证 | 5 | 4.5% |
| **合计** | **112** | **100%** |

| 优先级 | 用例数量 |
|--------|----------|
| P0 | 78 |
| P1 | 34 |
