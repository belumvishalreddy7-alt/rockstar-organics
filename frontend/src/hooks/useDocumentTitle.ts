import { useEffect } from "react";

/**
 * Sets document.title for the lifetime of the calling component, restoring
 * the previous title on unmount. A full react-helmet dependency isn't
 * warranted for a single-tab-title concern - this covers the real SEO/UX
 * gap (every route showing the same static "Rockstar Organics" title from
 * index.html) without adding a package.
 */
export function useDocumentTitle(title: string): void {
  useEffect(() => {
    const previous = document.title;
    document.title = title;
    return () => {
      document.title = previous;
    };
  }, [title]);
}
