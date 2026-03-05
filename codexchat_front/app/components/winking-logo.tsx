"use client";

import { useEffect, useState } from "react";
import Image from "next/image";

const WINK_INTERVAL_MS = 7000;
const WINK_DURATION_MS = 250;

type WinkingLogoProps = {
  size?: number;
};

export default function WinkingLogo({ size = 112 }: WinkingLogoProps) {
  const [isWinking, setIsWinking] = useState(false);

  useEffect(() => {
    let timeoutId: number | undefined;
    const preloadImage = new window.Image();
    preloadImage.src = "/brand/gnome-wink.png";
    void preloadImage.decode?.().catch(() => undefined);

    const intervalId = window.setInterval(() => {
      setIsWinking(true);
      timeoutId = window.setTimeout(() => setIsWinking(false), WINK_DURATION_MS);
    }, WINK_INTERVAL_MS);

    return () => {
      window.clearInterval(intervalId);
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
  }, []);

  return (
    <Image
      src={isWinking ? "/brand/gnome-wink.png" : "/brand/gnome-default.png"}
      alt="CodexChat logo"
      width={size}
      height={size}
      priority
    />
  );
}
