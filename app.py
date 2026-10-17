import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="量本利决策智能体", layout="wide")
st.title("量本利决策智能体")
st.caption("CVP Decision Agent · 盈亏平衡 · 安全边际 · 目标利润 · 敏感性分析")

# ---------- 侧边栏：参数输入 ----------
with st.sidebar:
    st.header("经营参数")
    price = st.number_input("单价（元/件）", value=50.0, min_value=0.01, step=1.0)
    unit_vc = st.number_input("单位变动成本（元/件）", value=30.0, min_value=0.0, step=1.0)
    fixed_cost = st.number_input("固定成本（元）", value=100000.0, min_value=0.0, step=1000.0)
    volume = st.number_input("当前/预计销售量（件）", value=8000, min_value=0, step=100)
    target_profit = st.number_input("目标利润（元，可选）", value=50000.0, min_value=0.0, step=1000.0)

# ---------- 决策计算层 ----------
def cvp_core(price, unit_vc, fixed_cost, volume):
    ucm = price - unit_vc                    # 单位边际贡献
    cm_ratio = ucm / price if price else 0   # 边际贡献率
    bep_units = fixed_cost / ucm if ucm > 0 else float("inf")
    bep_sales = fixed_cost / cm_ratio if cm_ratio > 0 else float("inf")
    profit = ucm * volume - fixed_cost
    mos_units = volume - bep_units
    mos_ratio = mos_units / volume if volume else 0
    return {
        "单位边际贡献": ucm,
        "边际贡献率": cm_ratio,
        "盈亏平衡销售量": bep_units,
        "盈亏平衡销售额": bep_sales,
        "当前利润": profit,
        "安全边际量": mos_units,
        "安全边际率": mos_ratio,
    }

def sensitivity(price, unit_vc, fixed_cost, volume, delta=0.10):
    base = cvp_core(price, unit_vc, fixed_cost, volume)["当前利润"]
    results = []
    factors = {
        "单价": ("price", price),
        "单位变动成本": ("unit_vc", unit_vc),
        "固定成本": ("fixed_cost", fixed_cost),
        "销售量": ("volume", volume),
    }
    for name, (key, val) in factors.items():
        if val == 0:
            continue
        new_val = val * (1 + delta)
        if key == "price":
            new_profit = cvp_core(new_val, unit_vc, fixed_cost, volume)["当前利润"]
        elif key == "unit_vc":
            new_profit = cvp_core(price, new_val, fixed_cost, volume)["当前利润"]
        elif key == "fixed_cost":
            new_profit = cvp_core(price, unit_vc, new_val, volume)["当前利润"]
        else:
            new_profit = cvp_core(price, unit_vc, fixed_cost, new_val)["当前利润"]
        coef = ((new_profit - base) / abs(base)) / delta if base != 0 else float("nan")
        results.append({"因素": name, "敏感系数": coef})
    return pd.DataFrame(results).sort_values("敏感系数", key=abs, ascending=False)

m = cvp_core(price, unit_vc, fixed_cost, volume)

# ---------- 经营状态诊断 ----------
if m["当前利润"] > 0:
    if m["安全边际率"] >= 0.20:
        status, color = "安全盈利区", "green"
    else:
        status, color = "盈利但安全边际偏薄", "orange"
elif m["当前利润"] == 0:
    status, color = "盈亏临界点", "blue"
else:
    status, color = "亏损区", "red"

# ---------- 输出层：指标卡片 ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("当前利润", f"{m['当前利润']:,.0f} 元")
c2.metric("盈亏平衡销售量", f"{m['盈亏平衡销售量']:,.0f} 件" if m["盈亏平衡销售量"] != float("inf") else "不可达")
c3.metric("安全边际率", f"{m['安全边际率']:.2%}")
c4.metric("经营状态", status)

st.info(f"**决策提示**：当前经营状态为「{status}」。安全边际率反映企业距离保本点的缓冲空间，一般以 20%—30% 作为判断经营安全性的参考基准。")

# ---------- 目标利润分析 ----------
st.subheader("目标利润分析")
ucm = m["单位边际贡献"]
if ucm > 0:
    target_units = (target_profit + fixed_cost) / ucm
    st.write(f"要实现目标利润 **{target_profit:,.0f} 元**，所需销售量为 **{target_units:,.0f} 件**，对应销售额为 **{target_units * price:,.0f} 元**。")
    if volume < target_units:
        st.warning(f"当前销售量 {volume:,.0f} 件尚差 **{target_units - volume:,.0f} 件**，建议优先从敏感性最高的因素入手调整。")
    else:
        st.success(f"当前销售量已覆盖目标利润所需水平，超出 **{volume - target_units:,.0f} 件**。")
else:
    st.error("单位边际贡献 ≤ 0，每多卖一件反而多亏一件，需首先调整价格或单位变动成本结构。")

# ---------- 敏感性分析 ----------
st.subheader("利润敏感性分析（各因素 +10% 对利润的影响）")
sens_df = sensitivity(price, unit_vc, fixed_cost, volume)
st.dataframe(sens_df, use_container_width=True, hide_index=True)
top = sens_df.iloc[0]
st.caption(f"**决策优先级**：「{top['因素']}」的敏感系数绝对值最大（{top['敏感系数']:.2f}），意味着该因素每变动 1%，利润变动约 {abs(top['敏感系数']):.2f}%。在资源有限时，应优先管理该因素。")

# ---------- 盈亏平衡图 ----------
st.subheader("盈亏平衡图")
max_q = max(volume, m["盈亏平衡销售量"] * 1.5 if m["盈亏平衡销售量"] != float("inf") else volume * 1.5, 100)
qs = list(range(0, int(max_q) + 1, max(1, int(max_q / 100))))
sales_line = [price * q for q in qs]
cost_line = [fixed_cost + unit_vc * q for q in qs]

fig = go.Figure()
fig.add_trace(go.Scatter(x=qs, y=sales_line, mode="lines", name="销售收入"))
fig.add_trace(go.Scatter(x=qs, y=cost_line, mode="lines", name="总成本"))
if m["盈亏平衡销售量"] != float("inf") and m["盈亏平衡销售量"] <= max_q:
    fig.add_vline(x=m["盈亏平衡销售量"], line_dash="dash", line_color="gray",
                  annotation_text=f"盈亏平衡点 {m['盈亏平衡销售量']:,.0f} 件")
fig.add_vline(x=volume, line_dash="dot", line_color="blue", annotation_text=f"当前销量 {volume:,.0f} 件")
fig.update_layout(xaxis_title="销售量（件）", yaxis_title="金额（元）", hovermode="x unified", height=420)
st.plotly_chart(fig, use_container_width=True)

st.caption("量本利决策智能体")
