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
Equity:Budget:Balance:{name}      ← 预算余额（周期初 = 预算额，周期末 = 余额）
Equity:Budget:Income:{name}       ← 预算收入（周期初调整时的反向账户）
```

---

## 安装

```bash
git clone <your-repo-url> ~/parallel_budget
```

在 Beancount 账本中引入：

```beancount
plugin "parallel_budget"
option "insert_pythonpath" "TRUE"
```

> 如果 plugin 放在非标准路径，需要将脚本所在目录加入 `PYTHONPATH`，或在同目录存放并在主账本中用相对路径引用。

---

## 用法

### 定义预算

用 `custom` directive 定义预算：

```beancount
2026-01-01 custom "parallel_budget" "Life"       "monthly"  9600 CNY
2026-01-01 custom "parallel_budget" "Decoration" "once"     300000 CNY
2026-01-01 custom "parallel_budget" "Traffic"    "monthly"  500  CNY
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
  - 预算名 `Life` → 匹配 `Expenses:Life:Food`、`Expenses:Life:Rent` 等
  - 预算名 `Traffic` → 匹配 `Expenses:Traffic:Traffic`、`Expenses:Traffic:Gas` 等

### 查看预算状态

使用 `bean-query` 或 `bean-report` 查看 `Equity:Budget:Balance:{name}` 的余额：

```bash
bean-query data/main.beancount "SELECT date, account, position WHERE account ~ 'Equity:Budget:Balance'"
```

或使用 Fava 直接查看 Equity:Budget 分类下的账户余额。

---

## 示例

### 月度生活预算

```beancount
2026-01-01 custom "parallel_budget" "Life" "monthly" 9600 CNY

2026-01-03 * "永辉超市" "买菜"
    Expenses:Life:Food                          320.00 CNY
    Liabilities:Bank:BoC:CN

2026-01-10 * "滴滴出行" "打车"
    Expenses:Traffic:Traffic                     45.00 CNY
    Liabilities:Bank:BoC:CN
```

插件自动为第一笔交易增加平行账脚注：

```beancount
2026-01-03 * "永辉超市" "买菜"
    Expenses:Life:Food                          320.00 CNY
    Liabilities:Bank:BoC:CN
    Equity:Budget:Expenses:Life                 320.00 CNY
    Equity:Budget:Balance:Life                 -320.00 CNY
```

第二笔走 `Traffic` 不在 `Life` 前缀内，**不会**标记。

### 一次性预算

```beancount
2026-01-01 custom "parallel_budget" "Decoration" "once" 300000 CNY
```

适用于装修、大件采购等一次性支出，只在预算起始日做一次调整。

---

## 与内置 budget 对比

| 特性 | 内置 `budget` | parallel_budget |
|:--|:--|:--|
| 使用方式 | `bean-query` 专用语法 | 标准复式记账账户 |
| 可视化 | 需在 Fava 中启用 budget 报表 | Fava Equity 分类直接可见 |
| 周期管理 | 自动 | 交易驱动，余额归零 |
| 灵活度 | 固定语法 | 自定义名称 + 前缀匹配 |
| 冲突 | 与 `budget` directive 名称冲突 | 独立，不与内置功能冲突 |

---

## License

MIT