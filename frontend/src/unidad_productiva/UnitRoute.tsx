import type { ReactNode } from "react";
import { ProtectedRoute } from "../AuthContext";
import { ManagementLayout } from "../Layouts";

export function UnitRoute({ children }: { children: ReactNode }) {
  return (
    <ProtectedRoute roles={["PRODUCTIVE_UNIT_RESPONSIBLE", "EXPOSITOR"]}>
      <ManagementLayout area="productive-unit">{children}</ManagementLayout>
    </ProtectedRoute>
  );
}
