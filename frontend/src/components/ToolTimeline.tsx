import { useEffect } from "react";
import { motion } from "framer-motion";
import type { ToolCall } from "../lib/types";
import { playTick } from "../lib/sounds";
import { useI18n } from "../hooks/useI18n";

export function ToolTimeline({ calls }: { calls: ToolCall[] }) {
  const { t } = useI18n();
  useEffect(() => {
    if (calls.length) playTick();
  }, [calls.length]);
  return (
    <div className="tool-timeline">
      <h3>{t.toolCalls}</h3>
      {calls.map((call, index) => (
        <motion.div
          key={`${call.tool_name}-${index}`}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.08, duration: 0.18 }}
        >
          <span>{call.tool_name}</span>
          <small>{call.status} · {call.duration_ms}ms</small>
        </motion.div>
      ))}
    </div>
  );
}
