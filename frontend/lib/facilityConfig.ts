export interface FacilityConfig {
  name: string;
  location: string;
  timezone: string;
  areaSqFt: number;
  plantCapacity: string;
}

export const DEFAULT_FACILITY_CONFIG: FacilityConfig = {
  name: 'Senatria Corporation',
  location: 'Bengaluru, Karnataka, India',
  timezone: 'Asia/Kolkata',
  areaSqFt: 75000,
  plantCapacity: '240T Plant',
};
