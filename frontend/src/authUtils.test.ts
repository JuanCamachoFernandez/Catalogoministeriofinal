import{describe,expect,it}from'vitest';
import{dashboardFor,isStrongPassword}from'./authUtils';

describe('reglas de autenticación',()=>{
  it('envía administradores al panel administrativo',()=>{
    expect(dashboardFor('SUPERADMIN')).toBe('/admin');
    expect(dashboardFor('ADMIN_VICEMINISTERIO')).toBe('/admin');
    expect(dashboardFor('ADMIN')).toBe('/admin');
  });
  it('envía expositores a su panel',()=>{
    expect(dashboardFor('EXPOSITOR')).toBe('/unidad-productiva/productos');
    expect(dashboardFor('PRODUCTIVE_UNIT_RESPONSIBLE')).toBe('/unidad-productiva/productos');
  });
  it('valida todos los requisitos de contraseña',()=>{
    expect(isStrongPassword('Segura2026!')).toBe(true);
    expect(isStrongPassword('sinSimbolo2026')).toBe(false);
    expect(isStrongPassword('Corta1!')).toBe(false);
  });
});
