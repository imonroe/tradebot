import { useEffect, useState } from "react";

export function useApi<T>(url: string, interval?: number) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function fetchData() {
      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`${response.status}`);
        const json = await response.json();
        if (mounted) {
          setData(json);
          setLoading(false);
        }
      } catch (e) {
        if (mounted) {
          setError(e instanceof Error ? e.message : "Unknown error");
          setLoading(false);
        }
      }
    }

    fetchData();

    if (interval) {
      const id = setInterval(fetchData, interval);
      return () => {
        mounted = false;
        clearInterval(id);
      };
    }

    return () => {
      mounted = false;
    };
  }, [url, interval]);

  return { data, loading, error };
}
