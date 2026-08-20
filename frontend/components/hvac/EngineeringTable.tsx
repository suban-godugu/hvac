'use client';

import React from 'react';

export const EngineeringTable: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="eng-scroll rounded border border-white/[0.08]">
    <table className="bms-table">{children}</table>
  </div>
);
