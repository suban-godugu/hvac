'use client';

import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Radio } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatusBadge, toneForStatus } from '@/components/hvac/StatusBadge';
import { EmptyState } from '@/components/hvac/EmptyState';
import { hvacFetch } from '@/lib/api/client';
import { PLATFORM_POLL_MS } from '@/lib/hvac/poll';

export default function BmsPage() {
  const qc = useQueryClient();
  const [protocol, setProtocol] = useState('bacnet');
  const [host, setHost] = useState('');
  const [port, setPort] = useState('47808');
  const [message, setMessage] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [mapForm, setMapForm] = useState({ equipment_id: 'AHU-01', canonical_point: 'supply_air_temperature', bms_point_id: '', direction: 'READ' });

  const status = useQuery({
    queryKey: ['bms-status'],
    queryFn: async () => (await hvacFetch('/api/platform/bms/status')).json(),
    refetchInterval: PLATFORM_POLL_MS,
  });
  const devices = useQuery({
    queryKey: ['bms-devices'],
    queryFn: async () => (await hvacFetch('/api/platform/bms/devices')).json(),
    refetchInterval: PLATFORM_POLL_MS,
  });
  const mappings = useQuery({
    queryKey: ['bms-mappings'],
    queryFn: async () => (await hvacFetch('/api/platform/bms/mappings')).json(),
    refetchInterval: PLATFORM_POLL_MS,
  });
  const points = useQuery({
    queryKey: ['bms-points', selected],
    queryFn: async () => {
      if (!selected) return { points: [] };
      return (await hvacFetch(`/api/platform/bms/devices/${selected}/points`)).json();
    },
    enabled: Boolean(selected),
  });

  const post = useMutation({
    mutationFn: async (path: string) => {
      const res = await hvacFetch(path, {
        method: 'POST',
        body: JSON.stringify({ protocol, host, port: Number(port) || 47808 }),
      });
      return res.json();
    },
    onSuccess: (body) => {
      setMessage(body.message || body.status || body.code || null);
      qc.invalidateQueries();
    },
  });

  const connect = (testOnly: boolean) =>
    hvacFetch('/api/platform/bms/connect', {
      method: 'POST',
      body: JSON.stringify({ protocol, host, port: Number(port) || 47808, test_only: testOnly }),
    }).then(async (res) => {
      const body = await res.json();
      setMessage(body.message || body.status || body.code || null);
      qc.invalidateQueries();
    });

  const saveMap = () =>
    hvacFetch('/api/platform/bms/mappings', {
      method: 'PUT',
      body: JSON.stringify({ ...mapForm, safety_enabled: true }),
    }).then(async (res) => {
      const body = await res.json();
      setMessage(body.message || 'MAPPING SAVED');
      qc.invalidateQueries();
    });

  const st = status.data || {};
  const deviceRows = devices.data?.devices || [];
  const pointRows = points.data?.points || [];
  const mapRows = mappings.data?.mappings || [];
  const catalog = mappings.data?.catalog || [];
  const livePlant = st.plantMode === 'LIVE_BMS';
  const defaultPorts: Record<string, string> = { bacnet: '47808', modbus: '502', mqtt: '1883', rest: '443' };

  return (
    <div className="space-y-6 pb-12">
      <PageHeader icon={Radio} title="BMS Connection" subtitle="Commissioning console. Discovery and mapping only." badge="READ-ONLY" />
      <div className="rounded-xl border border-amber-400/25 bg-amber-500/[0.08] px-4 py-3 text-[12px] text-amber-100" role="status">
        READ-ONLY COMMISSIONING — BMS writes are disabled. Map only discovered points.
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
      <section className="glass-card p-5 space-y-4 xl:col-span-5">
        <div className="text-[11px] font-semibold tracking-[0.14em] text-slate-500 uppercase">BMS Connection</div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <label className="text-[11px] text-slate-400 space-y-1.5">
            Protocol
            <select
              value={protocol}
              onChange={(e) => {
                const next = e.target.value;
                setProtocol(next);
                setPort(defaultPorts[next] || '47808');
              }}
              className="form-control"
            >
              <option value="bacnet">BACnet/IP</option>
              <option value="modbus">Modbus TCP</option>
              <option value="mqtt">MQTT</option>
              <option value="rest">REST</option>
            </select>
          </label>
          <label className="text-[11px] text-slate-400 space-y-1.5">
            Host
            <input value={host} onChange={(e) => setHost(e.target.value)} placeholder="gateway IP" className="form-control" />
          </label>
          <label className="text-[11px] text-slate-400 space-y-1.5">
            Port
            <input value={port} onChange={(e) => setPort(e.target.value)} className="form-control" />
          </label>
          <div className="flex items-end pb-0.5">
            <StatusBadge tone={toneForStatus(st.status)}>{st.status || 'DISCONNECTED'}</StatusBadge>
          </div>
        </div>
        <div className="text-[11px] font-mono text-slate-500">
          Last connected: {st.last_connected_at || '—'} · Last error: {st.last_error || '—'} · Protocol: {st.protocol || protocol}
        </div>
        {!livePlant && (
          <div className="text-[11px] text-amber-200">
            Switch the header to Live BMS before CONNECT. Dataset mode never opens a production gateway.
          </div>
        )}
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-ghost" onClick={() => connect(true)}>
            TEST CONNECTION
          </button>
          <button type="button" className="btn-primary" onClick={() => connect(false)} disabled={!livePlant || !host.trim()}>
            CONNECT
          </button>
          <button type="button" className="btn-ghost" onClick={() => post.mutate('/api/platform/bms/disconnect')}>
            DISCONNECT
          </button>
          <button type="button" className="btn-ghost" onClick={() => post.mutate('/api/platform/bms/discover')}>
            DISCOVER
          </button>
        </div>
        {message && <div className="text-[11px] font-mono text-amber-300">{message}</div>}
      </section>

      <div className="xl:col-span-7 space-y-4">
      <section className="glass-card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-[11px] font-semibold tracking-[0.12em] text-slate-400 uppercase">Devices</div>
          <StatusBadge tone="neutral" pulse={false}>
            {deviceRows.length} devices
          </StatusBadge>
        </div>
        {deviceRows.length === 0 ? (
          <EmptyState title="0 devices" detail="Connect and discover. Nothing is invented until the gateway returns devices." />
        ) : (
          <table className="bms-table">
            <thead>
              <tr>
                <th>Device</th>
                <th>Identifier</th>
                <th>Type</th>
                <th>Status</th>
                <th>Points</th>
              </tr>
            </thead>
            <tbody>
              {deviceRows.map((d: { id: string; name?: string; device_identifier: string; device_type?: string; status?: string; points?: number }) => (
                <tr key={d.id} className="cursor-pointer" onClick={() => setSelected(d.id)}>
                  <td className="text-slate-100">{d.name || d.device_identifier}</td>
                  <td className="font-mono text-slate-400">{d.device_identifier}</td>
                  <td>{d.device_type || '—'}</td>
                  <td>{d.status || '—'}</td>
                  <td>{d.points ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="glass-card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-[11px] font-semibold tracking-[0.12em] text-slate-400 uppercase">Points</div>
          <StatusBadge tone="neutral" pulse={false}>
            {pointRows.length} points
          </StatusBadge>
        </div>
        {pointRows.length === 0 ? (
          <EmptyState title="0 points" detail="Select a discovered device. Values stay empty until the BMS reports them." />
        ) : (
          <table className="bms-table">
            <thead>
              <tr>
                <th>Point</th>
                <th>Object Type</th>
                <th>Instance</th>
                <th>Unit</th>
                <th>R/W</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {pointRows.map((p: { id: string; point_identifier: string; object_type?: string; object_instance?: string; unit?: string; readable?: boolean; writable?: boolean; current_value?: number | null }) => (
                <tr key={p.id} className="cursor-pointer" onClick={() => setMapForm((f) => ({ ...f, bms_point_id: p.id }))}>
                  <td className="font-mono">{p.point_identifier}</td>
                  <td>{p.object_type || '—'}</td>
                  <td>{p.object_instance || '—'}</td>
                  <td>{p.unit || '—'}</td>
                  <td>
                    {p.readable ? 'R' : ''}
                    {p.writable ? 'W' : ''}
                  </td>
                  <td>{p.current_value == null ? '—' : p.current_value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      </div>
      </div>

      <section className="glass-card p-4 space-y-3">
        <div className="text-[11px] font-semibold tracking-[0.12em] text-slate-400 uppercase">Mapping</div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
          <input className="form-control" value={mapForm.equipment_id} onChange={(e) => setMapForm({ ...mapForm, equipment_id: e.target.value })} placeholder="AHU-01" />
          <select
            className="form-control"
            value={`${mapForm.equipment_id}.${mapForm.canonical_point}`}
            onChange={(e) => {
              const [eq, ...rest] = e.target.value.split('.');
              setMapForm({
                ...mapForm,
                equipment_id: eq || mapForm.equipment_id,
                canonical_point: rest.join('.') || mapForm.canonical_point,
              });
            }}
          >
            {(catalog.length
              ? catalog
              : [{ qualified: 'AHU-01.supply_air_temperature', equipment_id: 'AHU-01', canonical_point: 'supply_air_temperature' }]
            ).map((c: { qualified?: string; canonical_point: string; equipment_id?: string }) => {
              const q = c.qualified || `${c.equipment_id}.${c.canonical_point}`;
              return (
                <option key={q} value={q}>
                  {q}
                </option>
              );
            })}
          </select>
          <input className="form-control" value={mapForm.bms_point_id} onChange={(e) => setMapForm({ ...mapForm, bms_point_id: e.target.value })} placeholder="discovered point id" />
          <select className="form-control" value={mapForm.direction} onChange={(e) => setMapForm({ ...mapForm, direction: e.target.value })}>
            <option value="READ">READ</option>
            <option value="READ_WRITE">READ/WRITE</option>
          </select>
          <button type="button" className="btn-primary" onClick={saveMap} disabled={!mapForm.bms_point_id} title={!mapForm.bms_point_id ? 'Select a discovered BMS point first' : undefined}>
            SAVE MAPPING
          </button>
        </div>
        {mapRows.length === 0 ? (
          <EmptyState title="No mappings" detail="Select a discovered point, then save a canonical mapping. BACnet IDs are never invented here." />
        ) : (
          <table className="bms-table">
            <thead>
              <tr>
                <th>Canonical</th>
                <th>BMS Point</th>
                <th>Unit</th>
                <th>Direction</th>
                <th>Value</th>
                <th>Quality</th>
              </tr>
            </thead>
            <tbody>
              {mapRows.map((m: { id: string; qualified?: string; point_identifier?: string; unit?: string; direction?: string; current_value?: number | null; quality?: string }) => (
                <tr key={m.id}>
                  <td className="font-mono">{m.qualified}</td>
                  <td>{m.point_identifier || '—'}</td>
                  <td>{m.unit || '—'}</td>
                  <td>{m.direction}</td>
                  <td>{m.current_value == null ? '—' : m.current_value}</td>
                  <td>{m.quality || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="glass-card p-4 space-y-2">
        <div className="text-[11px] font-semibold tracking-[0.12em] text-slate-400 uppercase">Commissioning status</div>
        <div className="mt-2 text-sm text-slate-200">{st.write_enabled ? 'SUPERVISED WRITES ARMED' : 'READ-ONLY COMMISSIONING'}</div>
        <div className="text-[11px] font-mono text-slate-500 mt-1">
          HVAC_BMS_WRITE_ENABLED must be 1 on the server · BMS WRITE: {st.write_enabled ? 'ENABLED' : 'DISABLED'}
        </div>
        <div className="flex flex-wrap gap-2 pt-2">
          <button
            type="button"
            className="btn-primary"
            disabled={!livePlant || mapRows.length === 0}
            title="Requires Live BMS, mappings, HVAC_BMS_WRITE_ENABLED=1, and safety review"
            onClick={() =>
              hvacFetch('/api/platform/bms/write-enable', {
                method: 'POST',
                body: JSON.stringify({ confirm: true }),
              }).then(async (res) => {
                const body = await res.json();
                setMessage(body.message || body.code || body.status);
                qc.invalidateQueries();
              })
            }
          >
            ENABLE WRITES
          </button>
          <button
            type="button"
            className="btn-ghost"
            onClick={() =>
              hvacFetch('/api/platform/bms/write-disable', { method: 'POST' }).then(async (res) => {
                const body = await res.json();
                setMessage(body.message || body.code || 'WRITE_DISABLED');
                qc.invalidateQueries();
              })
            }
          >
            DISABLE WRITES
          </button>
        </div>
      </section>
    </div>
  );
}
