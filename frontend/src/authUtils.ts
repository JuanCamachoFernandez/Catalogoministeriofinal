export type UserRole='SUPERADMIN'|'ADMIN_VICEMINISTERIO'|'EXPOSITOR';

export function dashboardFor(role:UserRole){
  return role==='EXPOSITOR'?'/gestion/expositor/dashboard':'/gestion/admin/dashboard';
}

export function isStrongPassword(value:string){
  return value.length>=10&&/[A-Z]/.test(value)&&/[a-z]/.test(value)&&/[0-9]/.test(value)&&/[\W_]/.test(value);
}
