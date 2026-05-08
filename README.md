# parallel_budget — Beancount 平行预算插件

> 不使用 Beancount 内置 `budget` directive，**平行记账**。
> 每个周期自动调整余额至预算金额，过往周期余额自然归零。

---

## 原理

内置 `budget` 需要配合 `bean-query` 按特定语法使用，不够直观。
**parallel_budget** 采用「平行记账」思路：

1. **标记** — 每笔符合预算分类的支出自动附加 `Equity:Budget:Expenses:{name}` / `Equity:Budget:Balance:{name}` 脚注
2. **调整** — 每个周期（月/年/一次性）开头生成一笔交易，将 `Balance` 账户补/减到预算金额
3. **归零** — 过往周期的余额不累积，每周期重新从预算金额起步

### 账户体系

```
Equity:Budget:Expenses:{name}     ← 记录该预算下的实际支出
Equity:Budget:Balance:{name}      ← 预算余额（周期初 = 预算额，周期末 = 剩余）
Equity:Budget:Income:{name}       ← 预算收入（周期初调整时的反向账户）
```

---

## 安装

### 前提条件

- Beancount ≥ 2.3
- Python ≥ 3.8

### 步骤

```bash
git clone git@github.com:ertuil/beancount_parallel_budget.git ~/parallel_budget
```

在 Beancount 账本中引入：

```beancount
plugin "parallel_budget"
```

> **路径说明**：`plugin "parallel_budget"` 会尝试导入 `parallel_budget` 模块。
> 确保脚本所在目录在 `PYTHONPATH` 中，例如从仓库根目录运行：
> ```bash
> export PYTHONPATH=/path/to/parallel_budget:$PYTHONPATH
> bean-report /path/to/your/main.beancount
> ```
>
> 或者将 `parallel_budget.py` 复制到与你的账本文件相同（或更上层）的目录。

---

## 用法

### 定义预算

用 `custom` directive 定义预算：

```beancount
2026-01-01 custom "parallel_budget" "Food"       "monthly"  2000 USD
2026-01-01 custom "parallel_budget" "Renovation" "once"     20000 USD
2026-01-01 custom "parallel_budget" "Traffic"    "monthly"   500 USD
```

**语法：**

```
YYYY-MM-DD custom "parallel_budget" "<名称>" "<周期>" <金额> <币种>
```

| 参数 | 说明 |
|:--|:--|
| `名称` | 预算类别名称，会映射到 `Expenses:{name}` 及 `Equity:Budget:*:{name}` |
| `周期` | `monthly` / `yearly` / `once` / `daily` |
| `金额` | 每周期预算金额（数字） |
| `币种` | 货币单位，如 `CNY`、`USD` |

### 自动匹配规则

- 当一笔交易的 `Expenses` 账户以预算名称为**前缀**时，自动标记
  - 预算名 `Food` → 匹配 `Expenses:Food:Grocery`、`Expenses:Food:Dining` 等
  - 预算名 `Traffic` → 匹配 `Expenses:Transport:Taxi`（因为 `Transport` ≠ `Traffic`，**不匹配**）
- 严格前缀匹配，不是模糊搜索

### 查看预算状态

使用 `bean-query` 查看 `Equity:Budget:Balance:{name}` 的余额：

```bash
bean-query main.beancount "SELECT date, account, position WHERE account ~ 'Equity:Budget:Balance'"
```

或使用 Fava 直接查看 Equity:Budget 分类下的账户余额。

---

## 💡 预算周期结算与充值机制

这是理解 `parallel_budget` 的核心，建议仔细阅读 👇

### 核心逻辑

```
每个周期初 Balance = 预算金额
每笔支出      Balance -= 支出金额
周期末余额      → 下一个周期初重置回预算金额
```

### 逐月举例

假设一个 **Food** 预算，每月 **2000 USD**：

#### 1月

| 日期 | 事件 | Equity:Budget:Balance:Food 变化 | 余额 |
|:--:|:--|:--:|:--:|
| 1/1 | **周期初调整**（自动） | `+2000` | **2000** ← 充值 |
| 1/3 | Walmart 买菜 120.50 | `-120.50` | 1879.50 |
| 1/8 | DoorDash 午餐 32.00 | `-32.00` | 1847.50 |
| **1/31** | **1月末** | — | **1847.50** ← 未花完的结余 |

#### 2月

| 日期 | 事件 | Equity:Budget:Balance:Food 变化 | 余额 |
|:--:|:--|:--:|:--:|
| 2/1 | **周期初调整**（自动） | `+152.50` | **2000** ← 又充值了！ |
| 2/1 | Costco 235.00 | `-235.00` | 1765.00 |
| 2/20 | Whole Foods 78.00 | `-78.00` | 1687.00 |
| **2/28** | **2月末** | — | **1687.00** |

**注意到 2/1 的调整金额了吗？** 

插件计算了 1 月末余额是 **1847.50**，距离新周期预算 **2000** 还有 `+152.50` 的缺口，所以只补充了这个差额。这就是**充值**——不是粗暴地覆盖，而是精确补齐。

### 公式

```
PeriodStartAdj = BudgetAmount - RunningBalance

RunningBalance = 所有早于 period_start 的 Equity:Budget:Balance:{name} 的累计值
```

如果 `RunningBalance` 已经超过预算（超支），调整值为负数，表示需要从 Balance 中扣回：

```
例子：Budget 2000，上月末 Balance = 2230（超支 230）
→ PeriodStartAdj = 2000 - 2230 = -230  ← 扣回，Balance 回到 2000
```

### 一次性（once）周期

```
2026-01-01 custom "parallel_budget" "Renovation" "once" 20000 USD
```

只在起始日做一次调整，后续不再有充值动作。适合装修预算、大件采购等。

---

## 运行示例

仓库中包含一个可运行的示例账本：

```bash
cd ~/parallel_budget
make -C examples run
```

或手动运行：

```bash
cd ~/parallel_budget
PYTHONPATH=. bean-report examples/main.beancount
```

示例内容：
- **Food** 月度预算 2000 USD — 买菜、外卖等
- **Renovation** 一次性预算 20000 USD — 装修材料、人工

运行结果中会看到年度报告里出现 `Equity:Budget:*` 账户的余额和变动。

---

## 示例

### 月度预算

```beancount
2026-01-01 custom "parallel_budget" "Food" "monthly" 2000 USD

2026-01-03 * "Walmart" "Weekly groceries"
    Expenses:Food:Grocery                          120.50 USD
    Assets:CreditCard:Demo

2026-01-05 * "Uber" "Airport pickup"
    Expenses:Transport:Taxi                         45.00 USD
    Assets:CreditCard:Demo
```

插件自动为第一笔交易增加平行账脚注：

```beancount
2026-01-03 * "Walmart" "Weekly groceries"
    Expenses:Food:Grocery                          120.50 USD
    Assets:CreditCard:Demo
    Equity:Budget:Expenses:Food                    120.50 USD
    Equity:Budget:Balance:Food                    -120.50 USD
```

第二笔走 `Transport` 不在 `Food` 前缀内，**不会**标记。

### 一次性预算

```beancount
2026-01-01 custom "parallel_budget" "Renovation" "once" 20000 USD
```

适用于装修、大件采购等一次性支出，只在预算起始日做一次调整。

---

## 与内置 budget 对比

| 特性 | 内置 `budget` | parallel_budget |
|:--|:--|:--|
| 使用方式 | `bean-query` 专用语法 | 标准复式记账账户 |
| 可视化 | 需在 Fava 中启用 budget 报表 | Fava Equity 分类直接可见 |
| 周期管理 | 自动 | 交易驱动，余额自然归零并充值 |
| 灵活度 | 固定语法 | 自定义名称 + 前缀匹配 |
| 冲突 | 与 `budget` directive 名称冲突 | 独立，不与内置功能冲突 |

---

## 📝 生成声明

本插件的代码、文档和示例**全部由 OpenClaw + DeepSeek-v4-flash 生成**。

- 项目地址：https://github.com/ertuil/beancount_parallel_budget
- 同步镜像：https://git.elliot98.top/elliot/beancount_parallel_budget

---

## License

MIT