import { useState } from 'react';

export function Palm() {
  const [agreed, setAgreed] = useState(false);
  return (
    <div className="inner-page palm-page">
      <header className="page-heading"><div><p className="eyebrow">观掌纹 · 先观日常选择</p><h1>手相观照</h1></div><p>手掌图像属于敏感个人信息。功能开放前，我们先把隐私边界说清楚。</p></header>
      <div className="content-wrap palm-layout"><section className="palm-visual paper-panel"><div className="palm-hand"><i /><i /><i /><i /></div><div><small>图像即用即弃</small><b>不保存原图</b></div></section><section className="palm-copy"><p className="eyebrow dark">功能预览</p><h2>不是从掌纹里<br />断定你的一生。</h2><p>未来开放后，视觉模型只会描述掌纹的传统分类，并给出文化背景与自我观察问题。上传前需单独授权，处理完成后立即删除原图。</p><ul><li>不做人脸识别或身份确认</li><li>不保存、转售或用于训练</li><li>不输出疾病、寿命与灾祸判断</li></ul><label className="consent"><input type="checkbox" checked={agreed} onChange={(event) => setAgreed(event.target.checked)} /><span>我已理解图像处理方式，并愿意在功能开放后收到提示</span></label><button className="primary-button" disabled={!agreed}>功能准备中</button></section></div>
    </div>
  );
}
