'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import {
  ChevronDown,
  ChevronRight,
  LayoutDashboard,
  CalendarClock,
  Gauge,
  Wind,
  Zap,
  Wrench,
  Brain,
  Radio,
  Activity,
  Users,
} from 'lucide-react';
import { opportunitiesForSection } from '@/lib/hvac/opportunityConfig';
import { StatusBadge } from '@/components/hvac/StatusBadge';
import { useLiveTelemetry } from '@/lib/hvac/liveTelemetryStore';

export const Sidebar: React.FC = () => {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const resetMode = (searchParams.get('mode') || '').toUpperCase();

  const isSchedulingActive = pathname.startsWith('/agents/scheduling');
  const isPlantControlActive = pathname.startsWith('/agents/plant-control');
  const isVentilationActive = pathname.startsWith('/agents/ventilation-airflow');
  const isVariableSpeedActive = pathname.startsWith('/agents/variable-speed');
  const isOmActive = pathname.startsWith('/agents/operations-maintenance');

  const [open, setOpen] = useState({
    scheduling: isSchedulingActive,
    plant: isPlantControlActive,
    vent: isVentilationActive,
    vs: isVariableSpeedActive,
    om: isOmActive,
  });

  useEffect(() => {
    setOpen((prev) => ({
      scheduling: isSchedulingActive ? true : prev.scheduling,
      plant: isPlantControlActive ? true : prev.plant,
      vent: isVentilationActive ? true : prev.vent,
      vs: isVariableSpeedActive ? true : prev.vs,
      om: isOmActive ? true : prev.om,
    }));
  }, [isSchedulingActive, isPlantControlActive, isVentilationActive, isVariableSpeedActive, isOmActive]);

  const live = useLiveTelemetry();
  const bmsStatus = live.bmsStatus;
  const telemetryLabel = live.telemetryStatus;

  const isActive = (path: string) => pathname === path;
  const onTempReset = pathname.startsWith('/agents/plant-control/temperature-reset');

  let effectiveReset: 'HHW' | 'CHW' | 'CW' | null = null;
  if (onTempReset && resetMode === 'HHW') effectiveReset = 'HHW';
  else if (onTempReset && resetMode === 'CW') effectiveReset = 'CW';
  else if (onTempReset && (resetMode === 'CHW' || resetMode === '')) effectiveReset = 'CHW';

  const item = (active: boolean) =>
    `flex items-center gap-2 px-2.5 py-[7px] text-[11.5px] border-l-2 rounded-r-md transition-colors ${
      active
        ? 'border-cyan-400 text-cyan-100 bg-cyan-500/[0.12] font-semibold'
        : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
    }`;

  const Group: React.FC<{
    title: string;
    icon: React.ReactNode;
    expanded: boolean;
    onToggle: () => void;
    color: string;
    children: React.ReactNode;
  }> = ({ title, icon, expanded, onToggle, color, children }) => (
    <div className="pt-1">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-2 py-1.5 text-left text-[12px] font-semibold text-slate-300 hover:text-white rounded-md hover:bg-white/[0.03]"
      >
        <span className="flex items-center gap-2 min-w-0">
          <span style={{ color }}>{icon}</span>
          <span className="truncate">{title}</span>
        </span>
        {expanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-slate-500 shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-slate-500 shrink-0" />
        )}
      </button>
      {expanded && <div className="ml-1 mb-2 space-y-0.5">{children}</div>}
    </div>
  );

  const OppLink: React.FC<{ href: string; id: string; label?: string; active: boolean }> = ({
    href,
    id,
    label,
    active,
  }) => (
    <Link href={href} className={item(active)} title={label}>
      <span className={`font-mono w-8 shrink-0 ${active ? 'text-cyan-400' : 'text-slate-500'}`}>{id}</span>
      <span className="leading-snug truncate">{label}</span>
    </Link>
  );

  const scheduling = opportunitiesForSection('scheduling');
  const plant = opportunitiesForSection('plant-control');
  const vent = opportunitiesForSection('ventilation');
  const vs = opportunitiesForSection('variable-speed');
  const om = opportunitiesForSection('operations');

  return (
    <aside className="hvac-sidebar w-72 border-r border-white/[0.07] flex flex-col select-none h-[calc(100vh-4rem)] sticky top-16 overflow-hidden">
      <div className="px-4 py-3.5 border-b border-white/[0.06] shrink-0 bg-gradient-to-b from-cyan-500/[0.06] to-transparent">
        <div className="text-[10px] font-semibold tracking-[0.18em] text-slate-500 uppercase">Control Center</div>
        <div className="text-[11px] font-medium text-slate-300 mt-0.5">Twenty supervisory opportunities</div>
      </div>
      <nav className="p-2 space-y-0.5 flex-1 overflow-y-auto">
        <div className="px-2 pt-2 pb-1 text-[10px] font-semibold tracking-[0.16em] text-slate-600 uppercase">Platform</div>
        <Link href="/overview" className={item(isActive('/overview') || isActive('/'))}>
          <LayoutDashboard className="w-3.5 h-3.5 shrink-0" />
          Dashboard
        </Link>
        <Link href="/agents" className={item(isActive('/agents'))}>
          <Users className="w-3.5 h-3.5 shrink-0" />
          Systems
        </Link>
        <Link href="/platform/bms" className={item(pathname.startsWith('/platform/bms'))}>
          <Radio className="w-3.5 h-3.5 shrink-0" />
          Gateway
        </Link>
        <Link href="/platform/telemetry" className={item(pathname.startsWith('/platform/telemetry'))}>
          <Activity className="w-3.5 h-3.5 shrink-0" />
          Telemetry
        </Link>
        <Link href="/ml" className={item(isActive('/ml') || pathname.startsWith('/ml'))}>
          <Brain className="w-3.5 h-3.5 shrink-0" />
          ML Registry
        </Link>
        <div className="px-2 pt-4 pb-1 text-[10px] font-semibold tracking-[0.16em] text-slate-600 uppercase">Opportunities</div>
        <Group
          title="Scheduling"
          icon={<CalendarClock className="w-3.5 h-3.5" />}
          expanded={open.scheduling}
          onToggle={() => setOpen((s) => ({ ...s, scheduling: !s.scheduling }))}
          color="var(--cat-scheduling)"
        >
          <Link href="/agents/scheduling" className={item(isActive('/agents/scheduling'))}>
            Dashboard
          </Link>
          {scheduling.map((o) => (
            <OppLink
              key={o.id}
              href={o.route}
              id={o.id}
              label={o.shortLabel}
              active={pathname.startsWith(o.route) || (o.id === 'O1' && pathname.includes('optimum-start-stop'))}
            />
          ))}
        </Group>

        <Group
          title="Plant Control"
          icon={<Gauge className="w-3.5 h-3.5" />}
          expanded={open.plant}
          onToggle={() => setOpen((s) => ({ ...s, plant: !s.plant }))}
          color="var(--cat-plant)"
        >
          <Link href="/agents/plant-control" className={item(isActive('/agents/plant-control'))}>
            Dashboard
          </Link>
          <OppLink
            href="/agents/plant-control/duct-static-pressure"
            id="O5"
            label={plant.find((o) => o.id === 'O5')?.shortLabel}
            active={isActive('/agents/plant-control/duct-static-pressure')}
          />
          <div>
            <Link href="/agents/plant-control/temperature-reset" className={item(false)}>
              <span className="font-mono w-8 shrink-0 text-slate-500">O6–8</span>
              <span className="leading-snug truncate">Temperature Reset</span>
            </Link>
            <div className="ml-8 mt-0.5 space-y-0.5">
              <Link href="/agents/plant-control/temperature-reset?mode=HHW" className={item(effectiveReset === 'HHW')}>
                <span className={`font-mono w-8 shrink-0 ${effectiveReset === 'HHW' ? 'text-cyan-400' : 'text-slate-500'}`}>O6</span>
                Heating Hot Water
              </Link>
              <Link href="/agents/plant-control/temperature-reset?mode=CHW" className={item(effectiveReset === 'CHW')}>
                <span className={`font-mono w-8 shrink-0 ${effectiveReset === 'CHW' ? 'text-cyan-400' : 'text-slate-500'}`}>O7</span>
                Chilled Water
              </Link>
              <Link href="/agents/plant-control/temperature-reset?mode=CW" className={item(effectiveReset === 'CW')}>
                <span className={`font-mono w-8 shrink-0 ${effectiveReset === 'CW' ? 'text-cyan-400' : 'text-slate-500'}`}>O8</span>
                Condenser Water
              </Link>
            </div>
          </div>
          <OppLink
            href="/agents/plant-control/electronic-expansion-valve"
            id="O9"
            label={plant.find((o) => o.id === 'O9')?.shortLabel}
            active={isActive('/agents/plant-control/electronic-expansion-valve')}
          />
        </Group>

        <Group
          title="Ventilation"
          icon={<Wind className="w-3.5 h-3.5" />}
          expanded={open.vent}
          onToggle={() => setOpen((s) => ({ ...s, vent: !s.vent }))}
          color="var(--cat-ventilation)"
        >
          <Link href="/agents/ventilation-airflow" className={item(pathname === '/agents/ventilation-airflow')}>
            Dashboard
          </Link>
          {vent.map((o) => (
            <OppLink
              key={o.id}
              href={o.route}
              id={o.id}
              label={o.shortLabel}
              active={isActive(o.route) || (o.id === 'O10' && pathname.includes('outdoor-air'))}
            />
          ))}
        </Group>

        <Group
          title="Variable Speed"
          icon={<Zap className="w-3.5 h-3.5" />}
          expanded={open.vs}
          onToggle={() => setOpen((s) => ({ ...s, vs: !s.vs }))}
          color="var(--cat-variablespeed)"
        >
          <Link href="/agents/variable-speed" className={item(pathname === '/agents/variable-speed')}>
            Dashboard
          </Link>
          {vs.map((o) => (
            <OppLink key={o.id} href={o.route} id={o.id} label={o.shortLabel} active={isActive(o.route)} />
          ))}
        </Group>

        <Group
          title="Operations"
          icon={<Wrench className="w-3.5 h-3.5" />}
          expanded={open.om}
          onToggle={() => setOpen((s) => ({ ...s, om: !s.om }))}
          color="var(--cat-om)"
        >
          <Link href="/agents/operations-maintenance" className={item(pathname === '/agents/operations-maintenance')}>
            Dashboard
          </Link>
          {om.map((o) => (
            <OppLink key={o.id} href={o.route} id={o.id} label={o.shortLabel} active={isActive(o.route)} />
          ))}
        </Group>
      </nav>
      <div className="shrink-0 border-t border-white/[0.06] px-3 py-2.5 flex items-center gap-2 bg-[color:var(--bg-elevated)]">
        <StatusBadge tone={bmsStatus === 'CONNECTED' ? 'live' : 'muted'} pulse={bmsStatus === 'CONNECTED'}>
          BMS {bmsStatus}
        </StatusBadge>
        <StatusBadge tone={telemetryLabel === 'LIVE' ? 'live' : 'warn'} pulse={false}>
          TEL {telemetryLabel}
        </StatusBadge>
      </div>
    </aside>
  );
};
