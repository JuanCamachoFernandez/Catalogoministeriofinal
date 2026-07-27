import type { CanonicalFair } from "../api";

export type ActiveFairsResponse = {
  active: boolean;
  fair: CanonicalFair | null;
  items: CanonicalFair[];
};
