import { Controller, useFieldArray, useFormContext } from "react-hook-form"
import { useFrappeGetCall } from "frappe-react-sdk"
import { PlusIcon, Trash2Icon } from "lucide-react"
import { Button } from "@components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@components/ui/select"
import type { RavenSettings } from "@raven/types/Raven/RavenSettings"
import _ from "@lib/translate"

/** Effort sets an admin can offer for a model. "" = the model has no effort setting. */
const EFFORT_PRESETS = [
    { value: "low,medium,high", label: "Low · Medium · High" },
    { value: "minimal,low,medium,high", label: "Minimal · Low · Medium · High" },
    { value: "low,medium,high,xhigh", label: "Low · Medium · High · Extra high" },
    { value: "none,low,medium,high,xhigh", label: "None · Low · Medium · High · Extra high" },
]
// Radix Select cannot hold "" as an item value.
const NO_EFFORT = "__none__"

const effortsLabel = (efforts: string) => EFFORT_PRESETS.find((preset) => preset.value === efforts)?.label ?? efforts

/** Models users can pick in the Chatbot (first row = default), each with the efforts they may choose. */
export const ChatbotModelsField = ({ enabled }: { enabled: boolean }) => {
    const { control, formState } = useFormContext<RavenSettings>()
    const { fields, append, remove } = useFieldArray({ control, name: "chatbot_models" })
    const { data, error } = useFrappeGetCall<{ message: string[] }>(
        "raven.api.ai_features.get_chatbot_models", undefined, enabled ? undefined : null,
        { revalidateOnFocus: false, shouldRetryOnError: false },
    )
    const listed = data?.message ?? []

    return (
        <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between gap-2">
                <div>
                    <div className="text-base-medium text-ink-gray-8">{_("Chatbot Models")}</div>
                    <p className="text-p-sm text-ink-gray-5">
                        {error
                            ? _("Could not load models from OpenAI. Save a valid API key above, then reopen this page.")
                            : _("Users can only pick from these. The first model is the default.")}
                    </p>
                </div>
                <Button type="button" variant="outline" size="sm" disabled={formState.disabled}
                    onClick={() => append({ model: listed[0] ?? "", efforts: "low,medium,high" } as never)}>
                    <PlusIcon />{_("Add")}
                </Button>
            </div>
            {fields.map((row, index) => (
                <div key={row.id} className="grid grid-cols-[1fr_1fr_auto] items-center gap-2">
                    <Controller control={control} name={`chatbot_models.${index}.model`} rules={{ required: _("Model is required") }}
                        render={({ field }) => (
                            <Select value={field.value || undefined} onValueChange={field.onChange} disabled={formState.disabled}>
                                <SelectTrigger className="w-full" aria-label={_("Model in row {0}", [String(index + 1)])}><SelectValue placeholder={_("Select a model")} /></SelectTrigger>
                                <SelectContent>
                                    {[...new Set([...(field.value ? [field.value] : []), ...listed])].map((model) => <SelectItem key={model} value={model}>{model}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        )} />
                    <Controller control={control} name={`chatbot_models.${index}.efforts`}
                        render={({ field }) => (
                            <Select value={field.value || NO_EFFORT} onValueChange={(value) => field.onChange(value === NO_EFFORT ? "" : value)} disabled={formState.disabled}>
                                <SelectTrigger className="w-full" aria-label={_("Efforts in row {0}", [String(index + 1)])}><SelectValue>{field.value ? effortsLabel(field.value) : _("No effort setting")}</SelectValue></SelectTrigger>
                                <SelectContent>
                                    <SelectItem value={NO_EFFORT}>{_("No effort setting")}</SelectItem>
                                    {EFFORT_PRESETS.map((preset) => <SelectItem key={preset.value} value={preset.value}>{preset.label}</SelectItem>)}
                                    {field.value && !EFFORT_PRESETS.some((preset) => preset.value === field.value) && <SelectItem value={field.value}>{field.value}</SelectItem>}
                                </SelectContent>
                            </Select>
                        )} />
                    <Button type="button" variant="ghost" theme="red" size="sm" isIconButton aria-label={_("Remove model")} disabled={formState.disabled} onClick={() => remove(index)}>
                        <Trash2Icon />
                    </Button>
                </div>
            ))}
        </div>
    )
}
