import { buildOptions, validateConfig } from '../config.js';
import { setupAuth } from '../lib/auth.js';
import { executeUserJourney } from '../lib/user-journey.js';

export const options = buildOptions('spike');

export function setup() {
  validateConfig();
  return setupAuth();
}

export default function (data) {
  executeUserJourney(data.token);
}
