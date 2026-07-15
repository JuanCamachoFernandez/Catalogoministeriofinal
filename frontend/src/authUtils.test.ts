import{describe,expect,it}from'vitest';
import{dashboardFor,isStrongPassword}from'./authUtils';

describe('reglas de autenticación',()=>{
  it('envía administradores al panel administrativo',()=>{
    expect(dashboardFor('SUPERADMIN')).toBe('/gestion/admin/dashboard');
    expect(dashboardFor('ADMIN_VICEMINISTERIO')).toBe('/gestion/admin/dashboard');
  });
  it('envía expositores a su panel',()=>{
    expect(dashboardFor('EXPOSITOR')).toBe('/gestion/expositor/dashboard');
  });
  it('valida todos los requisitos de contraseña',()=>{
    expect(isStrongPassword('Segura2026!')).toBe(true);
    expect(isStrongPassword('sinSimbolo2026')).toBe(false);
    expect(isStrongPassword('Corta1!')).toBe(false);
  });
});
