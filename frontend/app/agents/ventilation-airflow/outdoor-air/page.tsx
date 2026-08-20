import { redirect } from 'next/navigation';

export default function OutdoorAirRedirectPage() {
  redirect('/agents/ventilation-airflow/economy-cycle');
}
