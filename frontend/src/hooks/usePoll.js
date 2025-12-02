import { useState, useEffect, useRef } from 'react';

const usePoll = (fetcher, interval = 2000) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const mountedRef = useRef(true);

    useEffect(() => {
        mountedRef.current = true;
        const fetchData = async () => {
            try {
                const result = await fetcher();
                if (mountedRef.current) {
                    setData(result);
                    setError(null);
                }
            } catch (err) {
                if (mountedRef.current) {
                    setError(err);
                }
            } finally {
                if (mountedRef.current) {
                    setLoading(false);
                }
            }
        };

        fetchData();
        const id = setInterval(fetchData, interval);

        return () => {
            mountedRef.current = false;
            clearInterval(id);
        };
    }, [fetcher, interval]);

    return { data, loading, error };
};

export default usePoll;
