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
  grid: 'rgba(26,26,29,0.08)',
  axis: '#64748b',
  current: '#8b5cf6',
  optimized: '#10b981',
  baseline: '#94a3b8',
};

export const EngineeringTooltip = (props: any) => {
  const { active, payload, label } = props;
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 shadow-lg rounded-xl px-2.5 py-2 text-[11px] font-mono">
      <div className="text-slate-500 mb-1">{label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="text-slate-700">
          {p.name}: <span className="text-violet-600 font-semibold">{p.value}</span>
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
