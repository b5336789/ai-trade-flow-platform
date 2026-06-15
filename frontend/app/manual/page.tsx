import Link from "next/link";
import {
  ArchitectureDiagram,
  ChartThumb,
  GraphThumb,
  PipelineDiagram,
  TableThumb,
} from "@/components/manual/Diagrams";

export const metadata = {
  title: "使用說明書 · AI Trade Flow",
};

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-4 space-y-3 border-t border-neutral-800 pt-6">
      <h2 className="text-xl font-bold text-neutral-100">{title}</h2>
      {children}
    </section>
  );
}

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-3 rounded-lg border border-neutral-800 bg-neutral-900/40 p-3">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-sm font-bold">
        {n}
      </div>
      <div className="space-y-1 text-sm text-neutral-300">
        <div className="font-semibold text-neutral-100">{title}</div>
        {children}
      </div>
    </div>
  );
}

function Code({ children }: { children: string }) {
  return (
    <pre className="overflow-x-auto rounded-lg border border-neutral-800 bg-neutral-950 p-3 text-xs text-neutral-200">
      <code>{children}</code>
    </pre>
  );
}

export default function Manual() {
  return (
    <main className="mx-auto max-w-4xl space-y-6 p-4 pb-16">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h1 className="text-3xl font-bold">使用說明書</h1>
          <p className="text-sm text-neutral-400">AI Trade Flow — 圖文並茂操作指南</p>
        </div>
        <Link href="/" className="rounded bg-neutral-800 px-3 py-1 text-sm hover:bg-neutral-700">
          ← 回到儀表板
        </Link>
      </header>

      <nav className="flex flex-wrap gap-2 text-sm">
        {[
          ["arch", "1 系統架構"],
          ["install", "2 安裝啟動"],
          ["ui", "3 介面導覽"],
          ["workflow", "4 建立工作流"],
          ["backtest", "5 回測/最佳化"],
          ["schedule", "6 自動執行"],
          ["ai", "7 AI 訊號"],
          ["safety", "8 安全須知"],
          ["markets", "9 支援市場"],
        ].map(([id, label]) => (
          <a key={id} href={`#${id}`} className="rounded bg-neutral-800/60 px-2 py-1 hover:bg-neutral-700">
            {label}
          </a>
        ))}
      </nav>

      <p className="rounded-lg border border-indigo-900 bg-indigo-950/40 p-3 text-sm text-indigo-200">
        本平台是一個 AI 驅動的自動交易系統:以視覺化「工作流」串接行情、技術指標/AI 訊號、風控與下單,
        可回測、最佳化參數,並定時自動執行。第一個完整打通的市場是<strong>加密貨幣(紙上交易)</strong>。
      </p>

      <Section id="arch" title="1 · 系統架構">
        <p className="text-sm text-neutral-300">
          使用者(或排程器)觸發<strong>工作流引擎</strong>;引擎依序執行各節點:抓行情 →
          產生訊號(技術指標或 AI)→ 經風控後下單。下單透過統一的 <strong>Broker</strong> 介面,
          可在「紙上/真實」與「不同市場」間切換。
        </p>
        <ArchitectureDiagram />
      </Section>

      <Section id="install" title="2 · 安裝與啟動">
        <Step n={1} title="設定環境變數">
          <p>複製範本並填入金鑰。<code>TRADING_MODE</code> 預設 <code>paper</code>(安全)。</p>
          <Code>{`cp .env.example .env
# 編輯 .env:設定 ANTHROPIC_API_KEY(AI 節點用)`}</Code>
        </Step>
        <Step n={2} title="用 Docker 一鍵啟動">
          <Code>{`docker compose up --build
# 後端  http://localhost:8000  (API 文件 /docs)
# 前端  http://localhost:3000`}</Code>
        </Step>
        <Step n={3} title="或本機分別啟動">
          <Code>{`# 後端
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]" && uvicorn app.main:app --reload

# 前端
cd frontend && npm install && npm run dev`}</Code>
        </Step>
      </Section>

      <Section id="ui" title="3 · 介面導覽">
        <p className="text-sm text-neutral-300">儀表板(首頁)分為以下面板:</p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <PanelCard title="Market 行情" desc="輸入代號看 K 線,按「AI Signal」取得 Claude 即時買賣建議。">
            <ChartThumb />
          </PanelCard>
          <PanelCard title="Workflow Builder" desc="拖拉節點組成交易流程,可 Save 儲存、Run 立即執行。">
            <GraphThumb />
          </PanelCard>
          <PanelCard title="Backtest 回測" desc="Run 單一回測、Compare all 比較策略、Optimize 最佳化參數。">
            <TableThumb />
          </PanelCard>
          <PanelCard title="Portfolio / Schedules / Notifications" desc="即時現金、部位、損益、訂單;排程讓工作流自動執行;成交與訊號即時通知(可外送 webhook)。">
            <TableThumb />
          </PanelCard>
        </div>
      </Section>

      <Section id="workflow" title="4 · 建立並執行工作流">
        <p className="text-sm text-neutral-300">
          一條典型流程:<strong>Data Source → 策略 / AI → Order → Logger</strong>。節點以連線傳遞資料。
        </p>
        <PipelineDiagram />
        <Step n={1} title="加入節點">
          於 Workflow Builder 點 <code>+ data_source</code>、<code>+ strategy</code>、<code>+ order</code> 等加入節點。
        </Step>
        <Step n={2} title="設定參數">
          在節點上填入 <code>symbol</code>(如 BTC/USDT)、策略名稱與參數、下單 <code>quantity</code>。
        </Step>
        <Step n={3} title="連線">
          從節點右側圓點拖到下一個節點左側,串成 data_source → strategy → order → logger。
        </Step>
        <Step n={4} title="執行或儲存">
          按 <strong>Run</strong> 立即執行(結果列在下方);按 <strong>Save</strong> 儲存以便排程。
          訊號為 hold 時不會下單。
        </Step>
      </Section>

      <Section id="backtest" title="5 · 回測與參數最佳化">
        <Step n={1} title="單一回測(Run)">
          選代號與策略、填參數,按 <strong>Run</strong>,看權益曲線與指標。
        </Step>
        <Step n={2} title="多策略比較(Compare all)">
          一次跑完所有策略,依報酬排名,🏆 標示最佳。
        </Step>
        <Step n={3} title="參數最佳化(Optimize)">
          對策略參數做網格搜尋,排名後可點「use」一鍵套用最佳參數。
        </Step>
        <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-3 text-sm text-neutral-300">
          <div className="mb-1 font-semibold text-neutral-100">指標解讀</div>
          <ul className="list-inside list-disc space-y-0.5">
            <li><strong>Return</strong>:策略總報酬率</li>
            <li><strong>Buy &amp; Hold</strong>:買入持有對照組</li>
            <li><strong>Max DD</strong>:最大回撤(越小越好)</li>
            <li><strong>Trades / Win%</strong>:交易次數與勝率</li>
          </ul>
        </div>
      </Section>

      <Section id="schedule" title="6 · 自動執行(排程)">
        <Step n={1} title="先 Save 工作流">在 Workflow Builder 按 Save,取得工作流編號。</Step>
        <Step n={2} title="建立排程">
          於 Schedules 面板選擇該工作流、設定間隔秒數(最少 5 秒),按 <strong>Schedule</strong>。
        </Step>
        <Step n={3} title="監看與控制">
          表格顯示每個排程的最後執行時間與狀態,可隨時 <strong>running/paused</strong> 切換或刪除。
        </Step>
        <p className="text-sm text-neutral-400">排程由後端 APScheduler 執行,每次觸發都會把結果寫入記錄。</p>
      </Section>

      <Section id="ai" title="7 · AI 訊號">
        <p className="text-sm text-neutral-300">
          AI 節點(或 Market 面板的「AI Signal」)會把精簡行情摘要交給 <strong>Claude</strong>,
          回傳結構化的 buy/sell/hold、信心度與<strong>白話理由</strong>。預設模型 <code>claude-opus-4-8</code>,
          需設定 <code>ANTHROPIC_API_KEY</code>。AI 訊號與技術指標策略在工作流中可互換。
        </p>
      </Section>

      <Section id="safety" title="8 · 安全須知">
        <div className="rounded-lg border border-amber-900 bg-amber-950/40 p-3 text-sm text-amber-100">
          <ul className="list-inside list-disc space-y-1">
            <li><strong>預設紙上交易</strong>:<code>TRADING_MODE=paper</code>,需明確改為 <code>live</code> 才會真實下單。</li>
            <li><strong>風控閘門</strong>:每筆下單前檢查單筆金額與部位總值上限,違規會被擋下。</li>
            <li><strong>金鑰安全</strong>:所有金鑰只存於 <code>.env</code>(已被 git 忽略),切勿寫死或提交。</li>
            <li><strong>務必先驗證</strong>:上線前以紙上交易與回測充分測試;真實交易具資金風險。</li>
          </ul>
        </div>
      </Section>

      <Section id="markets" title="9 · 支援市場">
        <table className="w-full text-left text-sm">
          <thead className="text-neutral-500">
            <tr>
              <th className="py-1">市場</th>
              <th>券商</th>
              <th>狀態</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-t border-neutral-800">
              <td className="py-1">加密貨幣</td>
              <td>Binance(ccxt)</td>
              <td className="text-green-400">✅ 行情 + 紙上交易(可選真實)</td>
            </tr>
            <tr className="border-t border-neutral-800">
              <td className="py-1">台股</td>
              <td>元大證券</td>
              <td className="text-yellow-400">⏳ 介面就緒,實作中</td>
            </tr>
            <tr className="border-t border-neutral-800">
              <td className="py-1">美股</td>
              <td>元大複委託 / Firstrade</td>
              <td className="text-yellow-400">⏳ 實作中(Firstrade 為非官方 API)</td>
            </tr>
          </tbody>
        </table>
        <p className="text-xs text-neutral-500">
          更深入的開發者文件見專案 <code>docs/</code> 目錄。
        </p>
      </Section>
    </main>
  );
}

function PanelCard({ title, desc, children }: { title: string; desc: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2 rounded-lg border border-neutral-800 bg-neutral-900/40 p-3">
      {children}
      <div className="text-sm font-semibold text-neutral-100">{title}</div>
      <p className="text-xs text-neutral-400">{desc}</p>
    </div>
  );
}
