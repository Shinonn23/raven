export type ChatbotModelOption = { model: string; efforts: string[] }
export type ChatbotChoice = { model: string; effort?: string }

const PREFERRED_EFFORT = "medium"

const EFFORT_LABELS: Record<string, string> = { none: "None", minimal: "Minimal", low: "Low", medium: "Medium", high: "High", xhigh: "Extra high", max: "Max" }

export const effortLabel = (effort: string) => EFFORT_LABELS[effort] ?? effort

const defaultEffort = (efforts: string[]) => (efforts.includes(PREFERRED_EFFORT) ? PREFERRED_EFFORT : efforts[0])

/**
 * The model and effort to use: what the user last picked while the admin still allows it,
 * otherwise the first allowed model with a sensible effort. Mirrors the server's own check.
 */
export const resolveChoice = (options: ChatbotModelOption[], stored?: ChatbotChoice): ChatbotChoice | undefined => {
    const option = options.find((candidate) => candidate.model === stored?.model) ?? options[0]
    if (!option) return undefined
    const effort = stored && option.model === stored.model && stored.effort && option.efforts.includes(stored.effort)
        ? stored.effort
        : defaultEffort(option.efforts)
    return { model: option.model, effort }
}

/** The current choice with another effort. Built from what is in use, so it also works before the user ever picked anything. */
export const withEffort = (choice: ChatbotChoice | undefined, effort: string): ChatbotChoice | undefined =>
    choice && { ...choice, effort }
