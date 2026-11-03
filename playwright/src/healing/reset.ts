import { resetHealingEvents } from './report';

/** Global setup. Clears healing events left by a previous run so the report only shows this run. */
export default async function resetHealing(): Promise<void> {
  resetHealingEvents();
}
