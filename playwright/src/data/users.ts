/**
 * Accounts published on the Swag Labs login page. They are public demo
 * credentials, not secrets, so they can live in the repository.
 */
export interface User {
  readonly username: string;
  readonly password: string;
  /** Short note on how the site treats this account. */
  readonly note: string;
}

const PASSWORD = 'secret_sauce';

export const users = {
  standard: { username: 'standard_user', password: PASSWORD, note: 'Normal account. Everything works.' },
  lockedOut: { username: 'locked_out_user', password: PASSWORD, note: 'Login is refused with a lock-out message.' },
  problem: { username: 'problem_user', password: PASSWORD, note: 'Logs in. Product images and some forms misbehave on purpose.' },
  performanceGlitch: {
    username: 'performance_glitch_user',
    password: PASSWORD,
    note: 'Logs in after a delay of several seconds.',
  },
} as const satisfies Record<string, User>;

/** Accounts the site lets in. Used for data-driven login tests. */
export const usersThatCanLogIn: readonly User[] = [users.standard, users.problem, users.performanceGlitch];

export type Users = typeof users;
