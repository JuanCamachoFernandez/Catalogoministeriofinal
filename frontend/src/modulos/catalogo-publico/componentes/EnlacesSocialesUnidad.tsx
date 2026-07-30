import type { ProductiveUnit } from "../../../compartido";

function FacebookIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M13.7 21v-8h2.7l.4-3h-3.1V8.1c0-.9.3-1.5 1.6-1.5H17V3.9c-.8-.1-1.5-.2-2.3-.2-2.3 0-3.9 1.4-3.9 4V10H8.2v3h2.6v8h2.9Z" />
    </svg>
  );
}

function InstagramIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="5" />
      <circle cx="12" cy="12" r="4.1" />
      <circle cx="17.4" cy="6.7" r="1" className="social-icon-fill" />
    </svg>
  );
}

function TikTokIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M15.6 3c.3 2.1 1.5 3.4 3.4 3.8v3a8 8 0 0 1-3.4-1v6.1a6.1 6.1 0 1 1-5.3-6.1v3.1a3.1 3.1 0 1 0 2.2 3V3h3.1Z" />
    </svg>
  );
}

export function EnlacesSocialesUnidad({ unit }: { unit: ProductiveUnit }) {
  const links = [
    {
      key: "facebook",
      label: "Facebook",
      url: unit.facebook_url,
      icon: <FacebookIcon />,
    },
    {
      key: "instagram",
      label: "Instagram",
      url: unit.instagram_url,
      icon: <InstagramIcon />,
    },
    {
      key: "tiktok",
      label: "TikTok",
      url: unit.tiktok_url,
      icon: <TikTokIcon />,
    },
  ].filter((link) => Boolean(link.url));

  if (!links.length) return null;

  return (
    <div className="unit-social-block">
      <span className="unit-social-title">Redes sociales</span>
      <nav className="unit-social-links" aria-label="Redes sociales">
        {links.map((link) => (
          <a
            key={link.key}
            className={`unit-social-button ${link.key}`}
            href={link.url ?? undefined}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Abrir ${link.label} de ${unit.nombre_comercial}`}
            title={link.label}
          >
            {link.icon}
          </a>
        ))}
      </nav>
    </div>
  );
}
