import { ChevronDown, Search, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export type OpcionBuscable = { value: string; label: string };

export function SelectorBuscable({
  value,
  options,
  onChange,
  placeholder = "Seleccione…",
  searchPlaceholder = "Buscar…",
  disabled = false,
  searchable = true,
  allowCustom = false,
  onDelete,
  ariaLabel,
  className = "",
}: {
  value: string;
  options: OpcionBuscable[];
  onChange: (value: string) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  disabled?: boolean;
  searchable?: boolean;
  allowCustom?: boolean;
  onDelete?: (option: OpcionBuscable) => void | Promise<void>;
  ariaLabel?: string;
  className?: string;
}) {
  const root = useRef<HTMLDivElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const selected = options.find((option) => option.value === value);
  const normalized = query.trim().toLocaleLowerCase("es");
  const filtered = searchable
    ? options.filter((option) =>
        option.label.toLocaleLowerCase("es").includes(normalized),
      )
    : options;
  const customValue = query.trim();
  const customExists = options.some(
    (option) =>
      option.label.toLocaleLowerCase("es") ===
      customValue.toLocaleLowerCase("es"),
  );

  useEffect(() => {
    const closeOutside = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", closeOutside);
    return () => document.removeEventListener("mousedown", closeOutside);
  }, []);

  const toggle = () => {
    if (disabled) return;
    setOpen((current) => {
      if (!current) {
        setQuery("");
        if (searchable) {
          setTimeout(() => search.current?.focus(), 0);
        }
      }
      return !current;
    });
  };
  const choose = (nextValue: string) => {
    onChange(nextValue);
    setOpen(false);
    setQuery("");
  };

  return (
    <div
      className={`searchable-select ${open ? "is-open" : ""} ${className}`.trim()}
      ref={root}
    >
      <button
        type="button"
        className="searchable-select-trigger"
        disabled={disabled}
        aria-label={ariaLabel}
        aria-expanded={open}
        aria-haspopup="listbox"
        onClick={toggle}
      >
        <span className={selected || value ? "" : "placeholder"}>
          {(selected?.label ?? value) || placeholder}
        </span>
        <ChevronDown size={18} />
      </button>
      {open && (
        <div className="searchable-select-menu">
          {searchable && (
            <label className="searchable-select-search">
              <Search size={17} />
              <input
                ref={search}
                value={query}
                placeholder={searchPlaceholder}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Escape") setOpen(false);
                  if (
                    event.key === "Enter" &&
                    allowCustom &&
                    customValue &&
                    !customExists
                  ) {
                    event.preventDefault();
                    choose(customValue);
                  }
                }}
              />
            </label>
          )}
          <div className="searchable-select-options" role="listbox">
            {filtered.map((option) => (
              <div
                className={`searchable-select-option ${option.value === value ? "selected" : ""}`}
                key={option.value}
              >
                <button type="button" onClick={() => choose(option.value)}>
                  {option.label}
                </button>
                {onDelete && option.value && (
                  <button
                    type="button"
                    className="searchable-select-delete"
                    aria-label={`Eliminar ${option.label}`}
                    onClick={() => onDelete(option)}
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>
            ))}
            {searchable && allowCustom && customValue && !customExists && (
              <button
                type="button"
                className="searchable-select-custom"
                onClick={() => choose(customValue)}
              >
                Usar nueva opción: <strong>{customValue}</strong>
              </button>
            )}
            {!filtered.length && !(allowCustom && customValue) && (
              <p className="searchable-select-empty">Sin coincidencias</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}


