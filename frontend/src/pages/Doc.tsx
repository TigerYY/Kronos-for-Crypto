import { motion } from "framer-motion";
import type { Variants } from "framer-motion";

export default function Doc() {
  const containerVariants: Variants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.3,
        delayChildren: 0.2,
      },
    },
  };

  const itemVariants: Variants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { type: "spring", stiffness: 100 },
    },
  };

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-12">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="relative border-l-2 border-slate-700/50 space-y-16 pl-8"
      >
        {/* Section 1: The Past */}
        <motion.div variants={itemVariants} className="relative">
          <div className="absolute -left-[41px] top-1 bg-slate-900 border-2 border-cyan-500 rounded-full w-4 h-4 shadow-[0_0_10px_rgba(6,182,212,0.6)]"></div>
          <h2 className="text-2xl font-bold text-slate-100 flex items-center mb-4">
            <span className="bg-cyan-500/10 text-cyan-400 px-3 py-1 rounded-md text-sm mr-4 tracking-widest uppercase shadow-[inset_0_0_10px_rgba(6,182,212,0.2)]">
              Genesis
            </span>
            过去纪元：基础大模型 (Foundation Model)
          </h2>
          <div className="bg-slate-800/40 backdrop-blur-md rounded-2xl p-6 border border-slate-700/50 shadow-xl hover:shadow-[0_4px_30px_rgba(6,182,212,0.1)] transition-shadow duration-300">
            <p className="text-slate-300 leading-relaxed mb-4">
              Kronos (AAAI 2026) 是首个专为金融市场语言设计的开源基础预训练模型。将其视作金融界的 GPT，它在出厂前便吞放了全球
              <strong className="text-cyan-400 font-semibold"> 45+ 主流交易所 </strong>长达十余年的多品类海量真实历史切片。
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
              <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-700/30">
                <h3 className="text-cyan-400 text-sm font-bold mb-2">上帝视野的上下文 (Lookback)</h3>
                <p className="text-slate-400 text-sm">
                  默认接收 <code>400</code> 根 K 线的组合形态作为输入。若在日线级别推断，它等于在决策前秒速回顾了超过一年的宏观牛熊周期。
                </p>
              </div>
              <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-700/30">
                <h3 className="text-cyan-400 text-sm font-bold mb-2">多维特征离散化映射</h3>
                <p className="text-slate-400 text-sm">
                  将开/高/低/收/量（OHLCV）数据特征经过分桶归一化（Tokenizer）后，投影进自回归序列空间中进行下一个周期的预测。
                </p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Section 2: The Present */}
        <motion.div variants={itemVariants} className="relative">
          <div className="absolute -left-[41px] top-1 bg-slate-900 border-2 border-purple-500 rounded-full w-4 h-4 shadow-[0_0_10px_rgba(168,85,247,0.6)]"></div>
          <h2 className="text-2xl font-bold text-slate-100 flex items-center mb-4">
            <span className="bg-purple-500/10 text-purple-400 px-3 py-1 rounded-md text-sm mr-4 tracking-widest uppercase shadow-[inset_0_0_10px_rgba(168,85,247,0.2)]">
              Current
            </span>
            现在纪元：全栈量化工程系统 (Full-Stack Architecture)
          </h2>
          <div className="bg-slate-800/40 backdrop-blur-md rounded-2xl p-6 border border-slate-700/50 shadow-xl hover:shadow-[0_4px_30px_rgba(168,85,247,0.1)] transition-shadow duration-300">
            <p className="text-slate-300 leading-relaxed mb-6">
              目前的系统已不只是一个预测接口，而是一套拥有独立状态风控管理、微秒级前端大盘监控、与严谨评估沙盒的工业级架构。
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-slate-900/60 p-5 rounded-xl border-t-2 border-purple-500/50 hover:-translate-y-1 transition-transform">
                <div className="text-2xl mb-2">⚖️</div>
                <h4 className="text-slate-200 font-semibold mb-1">多时框决策融合</h4>
                <p className="text-slate-400 text-xs leading-relaxed">基于尺度乘数 (TF_SCALE_FACTORS)，将 15m 到 1d 的短中长预测进行波动率无量纲化处理后的加权投票系统。</p>
              </div>
              <div className="bg-slate-900/60 p-5 rounded-xl border-t-2 border-blue-500/50 hover:-translate-y-1 transition-transform">
                <div className="text-2xl mb-2">🛡️</div>
                <h4 className="text-slate-200 font-semibold mb-1">物理约束防越界</h4>
                <p className="text-slate-400 text-xs leading-relaxed">在对抗生成推理回路中嵌套绝对几何限制 (High≥Close), 拦截常识级幻觉与静默标的的离群噪音爆炸。</p>
              </div>
              <div className="bg-slate-900/60 p-5 rounded-xl border-t-2 border-emerald-500/50 hover:-translate-y-1 transition-transform">
                <div className="text-2xl mb-2">🚦</div>
                <h4 className="text-slate-200 font-semibold mb-1">无状态回测隔离</h4>
                <p className="text-slate-400 text-xs leading-relaxed">废除持久化缓存以避免磁盘幽灵仓位串流，辅以双轨 Benchmark 同层对比展现真实的量化 Alpha。</p>
              </div>
              <div className="bg-slate-900/60 p-5 rounded-xl border-t-2 border-rose-500/50 hover:-translate-y-1 transition-transform">
                <div className="text-2xl mb-2">🎯</div>
                <h4 className="text-slate-200 font-semibold mb-1">贪婪稳定引擎</h4>
                <p className="text-slate-400 text-xs leading-relaxed">抛弃生成模型的核采样随机抖动，前端调用一律采用极低 Temperature 贪婪解码，使仪表分析输出硬核且稳定。</p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Section 3: The Future */}
        <motion.div variants={itemVariants} className="relative">
          <div className="absolute -left-[41px] top-1 bg-slate-900 border-2 border-fuchsia-500 rounded-full w-4 h-4 shadow-[0_0_10px_rgba(217,70,239,0.8)]"></div>
          <h2 className="text-2xl font-bold text-slate-100 flex items-center mb-4">
            <span className="bg-fuchsia-500/10 text-fuchsia-400 px-3 py-1 rounded-md text-sm mr-4 tracking-widest uppercase shadow-[inset_0_0_10px_rgba(217,70,239,0.2)]">
              Roadmap
            </span>
            未来进化路线：通向 AGI (Evolution Roadmap)
          </h2>
          <div className="bg-slate-800/40 backdrop-blur-md rounded-2xl p-6 border border-slate-700/50 shadow-xl">
            <div className="space-y-6 relative">

              {/* Timeline connecting line */}
              <div className="absolute left-4 top-4 bottom-4 w-px bg-slate-700/80 z-0"></div>

              <div className="relative z-10 flex gap-4 items-start group">
                <div className="w-8 h-8 rounded-full bg-slate-900 border border-fuchsia-500/50 flex items-center justify-center text-xs font-bold text-fuchsia-400 mt-1 shadow-[0_0_15px_rgba(217,70,239,0.2)] group-hover:scale-110 group-hover:bg-fuchsia-500/20 transition-all">01</div>
                <div className="flex-1 bg-slate-900/50 p-4 rounded-xl border border-slate-700/50 group-hover:border-fuchsia-500/30 transition-colors">
                  <h3 className="text-slate-200 font-bold mb-1">领域特化微调 (Domain Fine-tuning)</h3>
                  <p className="text-slate-400 text-sm">冻结主干网络，运用 LoRA 等低秩适应参数微调技术。喂入高频震荡或特定币种（如 BTC 短线）清洗数据，使模型从全球均分退化为指定杀手领域的“专才”。</p>
                </div>
              </div>

              <div className="relative z-10 flex gap-4 items-start group">
                <div className="w-8 h-8 rounded-full bg-slate-900 border border-blue-500/50 flex items-center justify-center text-xs font-bold text-blue-400 mt-1 shadow-[0_0_15px_rgba(59,130,246,0.2)] group-hover:scale-110 group-hover:bg-blue-500/20 transition-all">02</div>
                <div className="flex-1 bg-slate-900/50 p-4 rounded-xl border border-slate-700/50 group-hover:border-blue-500/30 transition-colors">
                  <h3 className="text-slate-200 font-bold mb-1">外接多模态因子 (Multi-Modal & RAG)</h3>
                  <p className="text-slate-400 text-sm">突破纯 K 线形态局限。在推断输入序列 (Prompt Context) 中直接拼合链上（Whale Alert）资产转移流向、以及宏观情绪指数进行 MLP 降维，获得基本面的先知预判视角。</p>
                </div>
              </div>

              <div className="relative z-10 flex gap-4 items-start group">
                <div className="w-8 h-8 rounded-full bg-slate-900 border border-amber-500/50 flex items-center justify-center text-xs font-bold text-amber-400 mt-1 shadow-[0_0_15px_rgba(245,158,11,0.2)] group-hover:scale-110 group-hover:bg-amber-500/20 transition-all">03</div>
                <div className="flex-1 bg-slate-900/50 p-4 rounded-xl border border-slate-700/50 group-hover:border-amber-500/30 transition-colors">
                  <h3 className="text-slate-200 font-bold mb-1">量化强化学习对齐 (RLHF)</h3>
                  <p className="text-slate-400 text-sm">将预测目标从“监督学习”转轨至 PPO 算法对齐。以 <code>Reward = 净收益 - 回撤惩罚</code> 作为奖励因子，通过平行的无边界虚拟沙盘自行博弈，让模型彻底成长为一个拥有止损智慧的“理智对冲基金”。</p>
                </div>
              </div>

              <div className="relative z-10 flex gap-4 items-start group">
                <div className="w-8 h-8 rounded-full bg-slate-900 border border-rose-500/50 flex items-center justify-center text-xs font-bold text-rose-400 mt-1 shadow-[0_0_15px_rgba(244,63,94,0.2)] group-hover:scale-110 group-hover:bg-rose-500/20 transition-all">04</div>
                <div className="flex-1 bg-slate-900/50 p-4 rounded-xl border border-slate-700/50 group-hover:border-rose-500/30 transition-colors">
                  <h3 className="text-slate-200 font-bold mb-1">算力与宏大视野跃升 (Scaling Up)</h3>
                  <p className="text-slate-400 text-sm">大力出奇迹方向。将底层参数狂飙至百亿 (7B+) 规模，并从架构层面重写 Attention 计算量，将 Context Length 推平至万级线位，跨越维度掌握从秒级别至数十年的金融波函数分布。</p>
                </div>
              </div>

            </div>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
