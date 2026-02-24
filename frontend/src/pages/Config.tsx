import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getConfig, putConfig, type StrategyConfig } from "../api/client";
import "./Config.css";

export default function Config() {
  const queryClient = useQueryClient();
  const { data: config, isLoading } = useQuery({
    queryKey: ["config"],
    queryFn: getConfig,
  });

  const saveMutation = useMutation({
    mutationFn: putConfig,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["config"] }),
  });

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const data: StrategyConfig = {
      threshold: Number((form.querySelector("[name=threshold]") as HTMLInputElement)?.value) / 100,
      strong_threshold: Number((form.querySelector("[name=strong_threshold]") as HTMLInputElement)?.value) / 100,
      weights: {
        "5m": Number((form.querySelector("[name=w5m]") as HTMLInputElement)?.value),
        "15m": Number((form.querySelector("[name=w15m]") as HTMLInputElement)?.value),
        "1h": Number((form.querySelector("[name=w1h]") as HTMLInputElement)?.value),
      },
      buy_pct: Number((form.querySelector("[name=buy_pct]") as HTMLInputElement)?.value) / 100,
      max_exposure: Number((form.querySelector("[name=max_exposure]") as HTMLInputElement)?.value) / 100,
      stop_loss: Number((form.querySelector("[name=stop_loss]") as HTMLInputElement)?.value) / 100,
      take_profit: Number((form.querySelector("[name=take_profit]") as HTMLInputElement)?.value) / 100,
      min_confidence: Number((form.querySelector("[name=min_confidence]") as HTMLInputElement)?.value),
    };
    saveMutation.mutate(data);
  };

  if (isLoading || !config) {
    return <p>加载配置中…</p>;
  }

  return (
    <div className="config-page">
      <header className="main-header">
        <h1>策略配置</h1>
        <p>动态调整 Kronos 交易策略 · 风险管理 · 参数说明</p>
      </header>

      <form onSubmit={handleSubmit} className="config-form">
        <div className="config-grid">
          <section className="config-section">
            <h3>信号策略参数</h3>
            <label>
              买卖信号阈值（%）
              <input
                name="threshold"
                type="number"
                min={0.1}
                max={5}
                step={0.1}
                defaultValue={((config.threshold ?? 0.005) * 100).toFixed(1)}
              />
            </label>
            <label>
              强信号阈值（%）
              <input
                name="strong_threshold"
                type="number"
                min={0.5}
                max={10}
                step={0.5}
                defaultValue={((config.strong_threshold ?? 0.015) * 100).toFixed(1)}
              />
            </label>
            <h4>多时框权重</h4>
            <label>
              5m 权重
              <input
                name="w5m"
                type="number"
                min={0}
                max={1}
                step={0.05}
                defaultValue={(config.weights as Record<string, number>)?.["5m"] ?? 0.2}
              />
            </label>
            <label>
              15m 权重
              <input
                name="w15m"
                type="number"
                min={0}
                max={1}
                step={0.05}
                defaultValue={(config.weights as Record<string, number>)?.["15m"] ?? 0.3}
              />
            </label>
            <label>
              1h 权重
              <input
                name="w1h"
                type="number"
                min={0}
                max={1}
                step={0.05}
                defaultValue={(config.weights as Record<string, number>)?.["1h"] ?? 0.5}
              />
            </label>
          </section>
          <section className="config-section">
            <h3>风险管理参数</h3>
            <label>
              单次买入比例（%）
              <input
                name="buy_pct"
                type="number"
                min={1}
                max={50}
                step={1}
                defaultValue={((config.buy_pct ?? 0.15) * 100).toFixed(0)}
              />
            </label>
            <label>
              最大仓位比例（%）
              <input
                name="max_exposure"
                type="number"
                min={10}
                max={100}
                step={5}
                defaultValue={((config.max_exposure ?? 0.8) * 100).toFixed(0)}
              />
            </label>
            <label>
              止损比例（%）
              <input
                name="stop_loss"
                type="number"
                min={1}
                max={20}
                step={1}
                defaultValue={((config.stop_loss ?? 0.03) * 100).toFixed(0)}
              />
            </label>
            <label>
              止盈比例（%）
              <input
                name="take_profit"
                type="number"
                min={2}
                max={50}
                step={1}
                defaultValue={((config.take_profit ?? 0.08) * 100).toFixed(0)}
              />
            </label>
            <label>
              最小信号置信度
              <input
                name="min_confidence"
                type="number"
                min={0.1}
                max={0.9}
                step={0.05}
                defaultValue={config.min_confidence ?? 0.45}
              />
            </label>
          </section>
        </div>
        <div className="form-actions">
          <button type="submit" className="btn-primary" disabled={saveMutation.isPending}>
            {saveMutation.isPending ? "保存中…" : "应用配置"}
          </button>
          {saveMutation.isSuccess && <span className="success-msg">配置已保存</span>}
          {saveMutation.isError && (
            <span className="error-msg">{(saveMutation.error as Error).message}</span>
          )}
        </div>
      </form>
    </div>
  );
}
