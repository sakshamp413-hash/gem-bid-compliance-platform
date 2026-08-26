import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";

export default function ScoreGauge({ score }: { score: number }) {
  const color = score >= 80 ? "#15803d" : score >= 50 ? "#b45309" : "#b91c1c";
  const data = [{ value: score }, { value: 100 - score }];
  return (
    <div className="relative h-40 w-40">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            startAngle={90}
            endAngle={-270}
            innerRadius="72%"
            outerRadius="100%"
            strokeWidth={0}
            isAnimationActive={false}
          >
            <Cell fill={color} />
            <Cell fill="#e2e8f0" />
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-3xl font-bold" style={{ color }}>
          {score.toFixed(1)}
        </div>
        <div className="text-[11px] uppercase tracking-wide text-slate-500">out of 100</div>
      </div>
    </div>
  );
}