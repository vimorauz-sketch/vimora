/* Drawing kit for VIMORA service illustrations (320 x 200 canvas, flat warm style). */
import type { ReactNode } from "react";

export const C = {
  ink: "#26302c", ink2: "#3a4541", screen: "#fbf8f3", line: "#ddd3c6", soft: "#efe7dc", paper: "#ffffff",
  brown: "#a8683c", brownL: "#ecd2b8", green: "#5f8f6b", greenL: "#d3e6d7", blue: "#4f7bb0", blueL: "#d3e0f0",
  rose: "#c46d7b", roseL: "#f3d6db", gold: "#d39b3a", goldL: "#f5e4c0", violet: "#7d6bb0", violetL: "#e3ddf3", red: "#c9553f",
};

type Box = { x: number; y: number; w: number; h: number };
type Screen = (b: Box) => ReactNode;

/* ---------------------------------------------------------------- devices */
export function Laptop({ x = 76, y = 34, w = 168, screen }: { x?: number; y?: number; w?: number; screen?: Screen }) {
  const h = w * 0.62;
  const s = { x: x + 7, y: y + 7, w: w - 14, h: h - 12 };
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={9} fill={C.ink} />
      <rect {...s} width={s.w} height={s.h} rx={3} fill={C.screen} />
      <svg x={s.x} y={s.y} width={s.w} height={s.h} overflow="hidden">{screen?.({ x: 0, y: 0, w: s.w, h: s.h })}</svg>
      <path d={`M${x - 16} ${y + h} h${w + 32} l-6 9 h${-(w + 20)} z`} fill={C.ink2} />
      <rect x={x + w / 2 - 16} y={y + h} width={32} height={3} rx={1.5} fill={C.ink} />
    </g>
  );
}

export function Monitor({ x = 82, y = 26, w = 156, screen }: { x?: number; y?: number; w?: number; screen?: Screen }) {
  const h = w * 0.62;
  const s = { x: x + 6, y: y + 6, w: w - 12, h: h - 12 };
  return (
    <g>
      <rect x={x + w / 2 - 9} y={y + h} width={18} height={20} fill={C.ink2} />
      <rect x={x + w / 2 - 34} y={y + h + 18} width={68} height={7} rx={3.5} fill={C.ink} />
      <rect x={x} y={y} width={w} height={h} rx={8} fill={C.ink} />
      <rect x={s.x} y={s.y} width={s.w} height={s.h} rx={3} fill={C.screen} />
      <svg x={s.x} y={s.y} width={s.w} height={s.h} overflow="hidden">{screen?.({ x: 0, y: 0, w: s.w, h: s.h })}</svg>
    </g>
  );
}

export function Phone({ x = 136, y = 22, w = 64, screen, tilt = 0 }: { x?: number; y?: number; w?: number; screen?: Screen; tilt?: number }) {
  const h = w * 2;
  const s = { x: x + 4, y: y + 10, w: w - 8, h: h - 20 };
  return (
    <g transform={tilt ? `rotate(${tilt} ${x + w / 2} ${y + h / 2})` : undefined}>
      <rect x={x} y={y} width={w} height={h} rx={11} fill={C.ink} />
      <rect x={s.x} y={s.y} width={s.w} height={s.h} rx={4} fill={C.screen} />
      <svg x={s.x} y={s.y} width={s.w} height={s.h} overflow="hidden">{screen?.({ x: 0, y: 0, w: s.w, h: s.h })}</svg>
      <rect x={x + w / 2 - 8} y={y + 4} width={16} height={3} rx={1.5} fill={C.ink2} />
    </g>
  );
}

export function Tablet({ x = 96, y = 30, w = 128, screen }: { x?: number; y?: number; w?: number; screen?: Screen }) {
  const h = w * 0.74;
  const s = { x: x + 8, y: y + 8, w: w - 16, h: h - 16 };
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={10} fill={C.ink} />
      <rect x={s.x} y={s.y} width={s.w} height={s.h} rx={3} fill={C.screen} />
      <svg x={s.x} y={s.y} width={s.w} height={s.h} overflow="hidden">{screen?.({ x: 0, y: 0, w: s.w, h: s.h })}</svg>
    </g>
  );
}

export function Paper({ x, y, w = 70, h = 92, children, fold = true, rot = 0, fill = C.paper }: { x: number; y: number; w?: number; h?: number; children?: ReactNode; fold?: boolean; rot?: number; fill?: string }) {
  return (
    <g transform={rot ? `rotate(${rot} ${x + w / 2} ${y + h / 2})` : undefined}>
      <rect x={x + 3} y={y + 4} width={w} height={h} rx={4} fill="#000" opacity={0.08} />
      <path d={fold ? `M${x + 4} ${y} h${w - 18} l14 14 v${h - 18} a4 4 0 0 1 -4 4 h${-(w - 8)} a4 4 0 0 1 -4 -4 v${-(h - 8)} a4 4 0 0 1 4 -4z` : `M${x + 4} ${y} h${w - 8} a4 4 0 0 1 4 4 v${h - 8} a4 4 0 0 1 -4 4 h${-(w - 8)} a4 4 0 0 1 -4 -4 v${-(h - 8)} a4 4 0 0 1 4 -4z`} fill={fill} stroke={C.line} strokeWidth={1} />
      {fold && <path d={`M${x + w - 14} ${y} v10 a4 4 0 0 0 4 4 h10`} fill={C.soft} stroke={C.line} strokeWidth={1} />}
      {children}
    </g>
  );
}

export function Printer({ x = 96, y = 70 }: { x?: number; y?: number }) {
  return (
    <g>
      <rect x={x + 22} y={y - 34} width={84} height={40} rx={3} fill={C.paper} stroke={C.line} />
      <Lines x={x + 32} y={y - 24} w={60} n={3} gap={8} />
      <rect x={x} y={y} width={128} height={52} rx={10} fill={C.ink2} />
      <rect x={x + 8} y={y + 8} width={112} height={8} rx={4} fill={C.ink} />
      <circle cx={x + 108} cy={y + 32} r={4} fill={C.green} />
      <rect x={x + 14} y={y + 28} width={40} height={6} rx={3} fill={C.ink} />
      <rect x={x + 22} y={y + 44} width={84} height={34} rx={2} fill={C.paper} stroke={C.line} />
      <Lines x={x + 32} y={y + 54} w={56} n={2} gap={8} />
    </g>
  );
}

/* ---------------------------------------------------------------- content */
export function Lines({ x, y, w, n = 3, gap = 9, color = C.line, last = 0.6, sw = 4 }: { x: number; y: number; w: number; n?: number; gap?: number; color?: string; last?: number; sw?: number }) {
  return <g>{Array.from({ length: n }, (_, i) => <rect key={i} x={x} y={y + i * gap} width={i === n - 1 ? w * last : w} height={sw} rx={sw / 2} fill={color} />)}</g>;
}

export function Bar({ x, y, w, p, color = C.brown, h = 7 }: { x: number; y: number; w: number; p: number; color?: string; h?: number }) {
  return <g><rect x={x} y={y} width={w} height={h} rx={h / 2} fill={C.soft} /><rect x={x} y={y} width={w * p} height={h} rx={h / 2} fill={color} /></g>;
}

export function TitleBar({ b, color = C.soft }: { b: Box; color?: string }) {
  return <g><rect x={b.x} y={b.y} width={b.w} height={12} fill={color} />{[0, 1, 2].map((i) => <circle key={i} cx={b.x + 8 + i * 8} cy={b.y + 6} r={2.4} fill={[C.rose, C.gold, C.green][i]} />)}</g>;
}

export function Chart({ x, y, w, h, vals = [0.4, 0.7, 0.5, 0.9, 0.65], colors = [C.brown, C.green, C.gold, C.blue, C.rose] }: { x: number; y: number; w: number; h: number; vals?: number[]; colors?: string[] }) {
  const bw = w / (vals.length * 1.6);
  return <g>{vals.map((v, i) => <rect key={i} x={x + i * bw * 1.6} y={y + h - h * v} width={bw} height={h * v} rx={2} fill={colors[i % colors.length]} />)}<rect x={x - 3} y={y + h} width={w} height={1.5} fill={C.line} /></g>;
}

export function Grid({ x, y, cols = 4, rows = 4, cw = 26, ch = 11, head = C.greenL, hi }: { x: number; y: number; cols?: number; rows?: number; cw?: number; ch?: number; head?: string; hi?: [number, number] }) {
  const cells: ReactNode[] = [];
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const isHi = hi && hi[0] === r && hi[1] === c;
    cells.push(<rect key={`${r}-${c}`} x={x + c * cw} y={y + r * ch} width={cw} height={ch} fill={r === 0 ? head : isHi ? C.goldL : C.paper} stroke={isHi ? C.gold : C.line} strokeWidth={isHi ? 1.5 : 0.8} />);
  }
  return <g>{cells}</g>;
}

export function Pie({ cx, cy, r, parts = [0.45, 0.3, 0.25], colors = [C.brown, C.green, C.gold] }: { cx: number; cy: number; r: number; parts?: number[]; colors?: string[] }) {
  let a = -Math.PI / 2;
  return <g>{parts.map((p, i) => {
    const a2 = a + p * Math.PI * 2;
    const d = `M${cx} ${cy} L${cx + r * Math.cos(a)} ${cy + r * Math.sin(a)} A${r} ${r} 0 ${p > 0.5 ? 1 : 0} 1 ${cx + r * Math.cos(a2)} ${cy + r * Math.sin(a2)} Z`;
    a = a2;
    return <path key={i} d={d} fill={colors[i % colors.length]} />;
  })}</g>;
}

export function Code({ x, y, w, n = 6 }: { x: number; y: number; w: number; n?: number }) {
  const pal = [C.violet, C.brown, C.green, C.blue, C.rose, C.gold];
  const widths = [0.5, 0.75, 0.6, 0.85, 0.4, 0.7, 0.55, 0.8];
  return <g>{Array.from({ length: n }, (_, i) => {
    const ind = [0, 10, 10, 20, 10, 0, 10, 20][i % 8]!;
    return <g key={i}><rect x={x + ind} y={y + i * 9} width={w * 0.18} height={4} rx={2} fill={pal[i % pal.length]} /><rect x={x + ind + w * 0.2} y={y + i * 9} width={(w - ind) * widths[i % widths.length]! * 0.6} height={4} rx={2} fill={C.line} /></g>;
  })}</g>;
}

export function Bubble({ x, y, w, h = 18, me = false, color }: { x: number; y: number; w: number; h?: number; me?: boolean; color?: string }) {
  return <g><rect x={x} y={y} width={w} height={h} rx={8} fill={color ?? (me ? C.brown : C.soft)} /><rect x={x + 7} y={y + h / 2 - 2} width={w * 0.6} height={4} rx={2} fill={me ? "#ffffff" : C.line} opacity={me ? 0.75 : 1} /></g>;
}

export function Mountain({ x, y, w, h, sky = C.blueL }: { x: number; y: number; w: number; h: number; sky?: string }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={3} fill={sky} />
      <circle cx={x + w * 0.74} cy={y + h * 0.3} r={h * 0.12} fill={C.gold} />
      <path d={`M${x} ${y + h} L${x + w * 0.32} ${y + h * 0.45} L${x + w * 0.55} ${y + h * 0.75} L${x + w * 0.72} ${y + h * 0.58} L${x + w} ${y + h} Z`} fill={C.green} />
    </g>
  );
}

export function Person({ cx, cy, r = 14, shirt = C.brown, skin = "#e6b796", hair = C.ink2 }: { cx: number; cy: number; r?: number; shirt?: string; skin?: string; hair?: string }) {
  return (
    <g>
      <path d={`M${cx - r * 1.5} ${cy + r * 2.6} a${r * 1.5} ${r * 1.4} 0 0 1 ${r * 3} 0 z`} fill={shirt} />
      <circle cx={cx} cy={cy} r={r} fill={skin} />
      <path d={`M${cx - r} ${cy - 1} a${r} ${r} 0 0 1 ${r * 2} 0 q${-r * 0.4} ${-r * 0.55} ${-r} ${-r * 0.5} q${-r * 0.6} 0 ${-r} ${r * 0.5}z`} fill={hair} />
    </g>
  );
}

export function Play({ cx, cy, r = 14, color = C.brown }: { cx: number; cy: number; r?: number; color?: string }) {
  return <g><circle cx={cx} cy={cy} r={r} fill={color} /><path d={`M${cx - r * 0.3} ${cy - r * 0.45} L${cx + r * 0.5} ${cy} L${cx - r * 0.3} ${cy + r * 0.45} Z`} fill="#fff" /></g>;
}

export function Wave({ x, y, w, h, color = C.brown, n = 22 }: { x: number; y: number; w: number; h: number; color?: string; n?: number }) {
  const step = w / n;
  return <g>{Array.from({ length: n }, (_, i) => {
    const v = 0.25 + 0.75 * Math.abs(Math.sin(i * 1.7) * Math.cos(i * 0.6));
    return <rect key={i} x={x + i * step} y={y + (h - h * v) / 2} width={step * 0.55} height={h * v} rx={1.5} fill={color} />;
  })}</g>;
}

/* ---------------------------------------------------------------- badges & glyphs */
export function Badge({ cx, cy, r = 17, fill = C.brown, children }: { cx: number; cy: number; r?: number; fill?: string; children?: ReactNode }) {
  return <g><circle cx={cx} cy={cy + 2} r={r} fill="#000" opacity={0.1} /><circle cx={cx} cy={cy} r={r} fill={fill} /><g color={fill} transform={`translate(${cx} ${cy}) scale(${r / 17})`}>{children}</g></g>;
}
// glyphs centred on 0,0 at r=17 scale, white strokes
const S = { fill: "none", stroke: "#fff", strokeWidth: 2.6, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
export const G = {
  check: <path d="M-7 0 l5 5 l9 -10" {...S} />,
  plus: <path d="M0 -7 v14 M-7 0 h14" {...S} />,
  down: <path d="M0 -8 v12 M-6 -2 l6 6 l6 -6 M-7 8 h14" {...S} />,
  up: <path d="M0 8 v-12 M-6 2 l6 -6 l6 6 M-7 -8 h14" {...S} />,
  bolt: <path d="M2 -9 l-8 11 h6 l-2 8 l8 -11 h-6 z" fill="#fff" />,
  lock: <g><rect x={-7} y={-2} width={14} height={10} rx={2} fill="#fff" /><path d="M-4 -2 v-3 a4 4 0 0 1 8 0 v3" {...S} /></g>,
  refresh: <path d="M7 -2 a7 7 0 1 0 -2 6 M7 -8 v6 h-6" {...S} />,
  heart: <path d="M0 7 c-9 -6 -9 -13 -4 -14 c2 0 3 1 4 3 c1 -2 2 -3 4 -3 c5 1 5 8 -4 14z" fill="#fff" />,
  star: <path d="M0 -8 l2.4 5 l5.6 .8 l-4 3.9 l1 5.6 l-5 -2.7 l-5 2.7 l1 -5.6 l-4 -3.9 l5.6 -.8z" fill="#fff" />,
  bell: <g><path d="M-6 4 v-4 a6 6 0 0 1 12 0 v4 l2 2 h-16z" fill="#fff" /><circle cx={0} cy={8} r={2} fill="#fff" /></g>,
  send: <path d="M-8 -1 l16 -7 l-6 16 l-3 -6 z" fill="#fff" />,
  globe: <g><circle r={8} {...S} /><path d="M-8 0 h16 M0 -8 c-5 5 -5 11 0 16 c5 -5 5 -11 0 -16" {...S} strokeWidth={2} /></g>,
  sparkle: <path d="M0 -9 c1 6 3 8 9 9 c-6 1 -8 3 -9 9 c-1 -6 -3 -8 -9 -9 c6 -1 8 -3 9 -9z" fill="#fff" />,
  pen: <path d="M-7 7 l2 -6 l9 -9 l4 4 l-9 9 z" fill="#fff" />,
  card: <g><rect x={-9} y={-6} width={18} height={12} rx={2} fill="#fff" /><rect x={-9} y={-3} width={18} height={3} fill="currentColor" /></g>,
  mail: <g><rect x={-9} y={-6} width={18} height={12} rx={2} fill="#fff" /><path d="M-8 -5 l8 6 l8 -6" fill="none" stroke="currentColor" strokeWidth={1.8} /></g>,
  pin: <g><path d="M0 9 c-6 -7 -7 -10 -7 -12 a7 7 0 0 1 14 0 c0 2 -1 5 -7 12z" fill="#fff" /><circle cy={-3} r={2.6} fill="currentColor" /></g>,
  bug: <g><ellipse rx={5} ry={7} fill="#fff" /><path d="M-5 -2 h-4 M5 -2 h4 M-5 3 h-4 M5 3 h4 M-2 -7 l-2 -3 M2 -7 l2 -3" {...S} strokeWidth={2} /></g>,
  chat: <path d="M-8 -6 h16 v10 h-9 l-5 4 v-4 h-2z" fill="#fff" />,
  shield: <g><path d="M0 -9 l7 3 v4 c0 5 -3 8 -7 10 c-4 -2 -7 -5 -7 -10 v-4z" fill="#fff" /><path d="M-3 0 l2 2 l4 -4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" /></g>,
  cap: <g><path d="M-10 -2 l10 -5 l10 5 l-10 5z" fill="#fff" /><path d="M-6 1 v4 c3 3 9 3 12 0 v-4" fill="#fff" /></g>,
  question: <g><path d="M-4 -4 a4 4 0 1 1 6 3.5 c-2 1 -2 2 -2 3.5" {...S} /><circle cy={7} r={1.6} fill="#fff" /></g>,
  scissors: <g><circle cx={-5} cy={5} r={3} {...S} strokeWidth={2} /><circle cx={5} cy={5} r={3} {...S} strokeWidth={2} /><path d="M-3 3 l9 -11 M3 3 l-9 -11" {...S} strokeWidth={2} /></g>,
  cc: <text x={0} y={4.5} textAnchor="middle" fontSize={11} fontWeight={700} fill="#fff" fontFamily="system-ui">CC</text>,
  wifi: <g><path d="M-9 -2 a13 13 0 0 1 18 0 M-6 2 a8 8 0 0 1 12 0" {...S} /><circle cy={6} r={2} fill="#fff" /></g>,
};

export function Wifi({ cx, cy, s = 1, color = C.brown }: { cx: number; cy: number; s?: number; color?: string }) {
  const st = { fill: "none", stroke: color, strokeWidth: 5 * s, strokeLinecap: "round" as const };
  return <g><path d={`M${cx - 26 * s} ${cy - 8 * s} a37 37 0 0 1 ${52 * s} 0`} {...st} /><path d={`M${cx - 16 * s} ${cy + 2 * s} a23 23 0 0 1 ${32 * s} 0`} {...st} /><circle cx={cx} cy={cy + 12 * s} r={5 * s} fill={color} /></g>;
}

export function Cloud({ cx, cy, s = 1, fill = C.paper }: { cx: number; cy: number; s?: number; fill?: string }) {
  return <path d={`M${cx - 30 * s} ${cy + 14 * s} a14 14 0 0 1 2 -28 a20 20 0 0 1 38 -6 a16 16 0 0 1 20 34 z`} fill={fill} stroke={C.line} strokeWidth={1.2} />;
}

export function Folder({ x, y, w = 60, h = 44, color = C.gold }: { x: number; y: number; w?: number; h?: number; color?: string }) {
  return <g><path d={`M${x} ${y + 6} a4 4 0 0 1 4 -4 h${w * 0.32} l6 6 h${w * 0.68 - 14} a4 4 0 0 1 4 4 v${h - 12} a4 4 0 0 1 -4 4 h${-(w - 4)} a4 4 0 0 1 -4 -4z`} fill={color} /><rect x={x} y={y + 14} width={w} height={h - 12} rx={4} fill={color} opacity={0.82} /></g>;
}

export function Gear({ cx, cy, r = 14, color = C.ink2 }: { cx: number; cy: number; r?: number; color?: string }) {
  const teeth = Array.from({ length: 8 }, (_, i) => {
    const a = (i * Math.PI) / 4;
    return <rect key={i} x={cx - r * 0.18} y={cy - r * 1.28} width={r * 0.36} height={r * 0.5} rx={1.5} fill={color} transform={`rotate(${(a * 180) / Math.PI} ${cx} ${cy})`} />;
  });
  return <g>{teeth}<circle cx={cx} cy={cy} r={r} fill={color} /><circle cx={cx} cy={cy} r={r * 0.42} fill={C.screen} /></g>;
}

export function Chip({ cx, cy, s = 22 }: { cx: number; cy: number; s?: number }) {
  const pins = Array.from({ length: 4 }, (_, i) => -s / 2 + (s / 5) * (i + 1));
  return (
    <g>
      {pins.map((p) => <g key={p}><rect x={cx + p - 1.5} y={cy - s / 2 - 6} width={3} height={6} fill={C.ink2} /><rect x={cx + p - 1.5} y={cy + s / 2} width={3} height={6} fill={C.ink2} /><rect x={cx - s / 2 - 6} y={cy + p - 1.5} width={6} height={3} fill={C.ink2} /><rect x={cx + s / 2} y={cy + p - 1.5} width={6} height={3} fill={C.ink2} /></g>)}
      <rect x={cx - s / 2} y={cy - s / 2} width={s} height={s} rx={4} fill={C.ink} />
      <rect x={cx - s / 4} y={cy - s / 4} width={s / 2} height={s / 2} rx={2} fill={C.green} />
    </g>
  );
}

export function Plant({ x, y, s = 1 }: { x: number; y: number; s?: number }) {
  return (
    <g>
      <path d={`M${x} ${y - 18 * s} c-14 -6 -14 -20 -6 -24 c4 8 8 14 6 24z`} fill={C.green} />
      <path d={`M${x} ${y - 16 * s} c12 -8 16 -18 10 -24 c-6 6 -10 14 -10 24z`} fill="#77a583" />
      <path d={`M${x - 10 * s} ${y - 18 * s} h${20 * s} l-3 ${18 * s} h${-14 * s}z`} fill={C.brown} />
    </g>
  );
}

export function Mug({ x, y }: { x: number; y: number }) {
  return <g><rect x={x} y={y} width={18} height={20} rx={3} fill={C.paper} stroke={C.line} /><path d={`M${x + 18} ${y + 5} a5 5 0 0 1 0 10`} fill="none" stroke={C.line} strokeWidth={3} /><path d={`M${x + 5} ${y - 4} q3 -4 0 -8 M${x + 11} ${y - 4} q3 -4 0 -8`} fill="none" stroke={C.line} strokeWidth={2} strokeLinecap="round" /></g>;
}

export function Txt({ x, y, children, size = 10, color = C.ink, weight = 700, anchor = "start", font = "system-ui, sans-serif" }: { x: number; y: number; children: ReactNode; size?: number; color?: string; weight?: number; anchor?: "start" | "middle" | "end"; font?: string }) {
  return <text x={x} y={y} fontSize={size} fill={color} fontWeight={weight} textAnchor={anchor} fontFamily={font}>{children}</text>;
}
