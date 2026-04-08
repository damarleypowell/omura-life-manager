/**
 * Omura Next.js App wrapper — global styles and toast provider.
 */

import '../styles/globals.css';
import { Toaster } from 'react-hot-toast';

export default function OmuraApp({ Component, pageProps }) {
  return (
    <>
      <Component {...pageProps} />
      <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
    </>
  );
}
