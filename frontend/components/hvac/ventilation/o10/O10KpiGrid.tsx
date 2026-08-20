'use client';

import { KPIGrid } from '@/components/hvac/KPIGrid';
import { formatAgeSeconds, formatDash, formatPercent } from '@/lib/hvac/formatters';
import { o10Enth, o10Num, o10Str, o10Temp } from '@/lib/hvac/o10Format';
import type { VentilationOpportunity } from '@/lib/hvac/ventilationTypes';

export function O10KpiGrid({ data }: { data: VentilationOpportunity }) {
  const items = [
    { label: 'Outdoor Air Temperature', value: o10Temp(data, 'outdoor_drybulb_c', 'outdoor_temp_c') },
    { label: 'Outdoor Air Relative Humidity', value: formatPercent(o10Num(data, 'outdoor_rh_pct', 'outdoor_rh_percent')) },
    { label: 'Outdoor Air Enthalpy', value: o10Enth(data, 'outdoor_enthalpy_kj_kg', 'outdoor_enthalpy_kjkg') },
    { label: 'Outdoor Air Dew Point', value: o10Temp(data, 'outdoor_dew_point_c', 'oa_dew_point_c') },
    { label: 'Return Air Temperature', value: o10Temp(data, 'return_drybulb_c', 'return_temp_c') },
    { label: 'Return Air Relative Humidity', value: formatPercent(o10Num(data, 'return_rh_pct', 'return_rh_percent')) },
    { label: 'Return Air Enthalpy', value: o10Enth(data, 'return_enthalpy_kj_kg', 'return_enthalpy_kjkg') },
    { label: 'Return Air Dew Point', value: o10Temp(data, 'return_dew_point_c', 'ra_dew_point_c') },
    { label: 'Zone Cooling Set Point', value: o10Temp(data, 'zone_cooling_setpoint_c', 'cooling_setpoint_c') },
    { label: 'Supply Air Temperature', value: o10Temp(data, 'supply_air_temp_c', 'supply_air_temperature_c') },
    { label: 'Mixed Air Temperature', value: o10Temp(data, 'mixed_air_temp_c', 'mixed_air_temperature_c') },
    { label: 'Outdoor Air Damper', value: formatPercent(data.current?.damperPct ?? o10Num(data, 'oa_damper_pct', 'current_value')) },
    { label: 'Return Air Damper', value: formatPercent(o10Num(data, 'return_damper_pct', 'ra_damper_pct')) },
    { label: 'Relief Air Damper', value: formatPercent(o10Num(data, 'relief_damper_pct')) },
    { label: 'Cooling Call', value: o10Str(data, 'cooling_call', 'cooling_demand') },
    { label: 'Cooling Valve', value: formatPercent(o10Num(data, 'cooling_valve_percent', 'cooling_valve_pct')) },
    { label: 'Fan Status', value: o10Str(data, 'fan_status', 'fan_state') },
    { label: 'Fan Command', value: o10Str(data, 'fan_command') },
    { label: 'Fire Mode', value: o10Str(data, 'fire_mode', 'fire_alarm') },
    { label: 'Occupancy / Schedule', value: o10Str(data, 'schedule_state', 'occupancy_state') },
    { label: 'Telemetry Quality', value: formatDash(data.telemetry?.quality) },
    { label: 'Telemetry Age', value: formatAgeSeconds(data.telemetry?.ageSeconds) },
  ];
  return (
    <section className="col-span-12" aria-label="O10 KPI grid">
      <KPIGrid emptyText="—" className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-3" items={items} />
    </section>
  );
}
