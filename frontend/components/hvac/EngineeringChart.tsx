'use client';

import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceLine,
  AreaChart,
  Area,
  BarChart,
  Bar,
  ScatterChart,
  Scatter,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

export const CHART_COLORS = {
  grid: 'rgba(255,255,255,0.06)',
  axis: '#64748b',
  current: '#22d3ee',
  optimized: '#34d399',
  baseline: '#94a3b8',
};

export const EngineeringTooltip = (props: any) => {
  const { active, payload, label } = props;
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#0c1220] border border-white/[0.08] px-2.5 py-2 text-[11px] font-mono">
      <div className="text-slate-400 mb-1">{label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="text-slate-200">
          {p.name}: <span className="text-cyan-300">{p.value}</span>
        </div>
      ))}
    </div>
  );
};

interface EngineeringChartProps {
  children: React.ReactNode;
  height?: number;
}

export const EngineeringChart: React.FC<EngineeringChartProps> = ({ children, height = 260 }) => (
  <div className="w-full" style={{ height }}>
    <ResponsiveContainer width="100%" height="100%">
      {children as React.ReactElement}
    </ResponsiveContainer>
  </div>
);

export { LineChart, Line, XAxis, YAxis, CartesianGrid, Legend, ReferenceLine, Tooltip, AreaChart, Area, ResponsiveContainer, BarChart, Bar, ScatterChart, Scatter, PieChart, Pie, Cell };
