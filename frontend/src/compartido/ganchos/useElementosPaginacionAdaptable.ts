import { useEffect, useRef, useState } from "react";
import type { Pagination } from "../../compartido";

export function usePaginacionMovil() {
  const getValue = () =>
    typeof window !== "undefined" && window.matchMedia
      ? window.matchMedia("(max-width: 760px)").matches
      : false;
  const [mobile, setMobile] = useState(getValue);
  useEffect(() => {
    if (!window.matchMedia) return undefined;
    const media = window.matchMedia("(max-width: 760px)");
    const update = () => setMobile(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return mobile;
}

/* The next page arrives asynchronously from the API, so the accumulated mobile
   list must be synchronized when that external result changes. */
/* eslint-disable react-hooks/set-state-in-effect */
export function useElementosPaginacionAdaptable<T extends { id?: string }>(
  items: T[],
  pagination: Pagination,
  resetKey = "",
) {
  const mobile = usePaginacionMovil();
  const [accumulated, setAccumulated] = useState<T[]>(items);
  const previousResetKey = useRef(resetKey);

  useEffect(() => {
    if (previousResetKey.current !== resetKey) {
      previousResetKey.current = resetKey;
      setAccumulated(pagination.page <= 1 ? items : []);
      return;
    }
    if (mobile && !items.length && !pagination.total) return;
    if (!mobile || pagination.page <= 1) {
      setAccumulated((current) =>
        current.length === items.length &&
        current.every((item, index) => item.id === items[index]?.id)
          ? current
          : items,
      );
      return;
    }
    if (!items.length) return;
    setAccumulated((current) => {
      const incoming = new Map(
        items.map((item, index) => [item.id ?? `incoming-${index}`, item]),
      );
      const known = new Set(current.map((item) => item.id).filter(Boolean));
      const updated = current.map((item) =>
        item.id && incoming.has(item.id) ? incoming.get(item.id)! : item,
      );
      for (const item of items) {
        if (!item.id || !known.has(item.id)) updated.push(item);
      }
      const unchanged =
        updated.length === current.length &&
        updated.every((item, index) => item === current[index]);
      return unchanged ? current : updated;
    });
  }, [items, mobile, pagination.page, pagination.total, resetKey]);

  return mobile ? accumulated : items;
}
/* eslint-enable react-hooks/set-state-in-effect */


