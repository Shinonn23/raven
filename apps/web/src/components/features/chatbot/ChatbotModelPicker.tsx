import { CheckIcon, ChevronDownIcon } from "lucide-react"
import { Button } from "@components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@components/ui/dropdown-menu"
import _ from "@lib/translate"
import { effortLabel } from "./chatbotChoice"
import { useChatbotChoice } from "./useChatbotChoice"

interface PickerProps {
    label: string
    value: string
    items: { value: string; label: string }[]
    onPick: (value: string) => void
}

const Picker = ({ label, value, items, onPick }: PickerProps) => (
    <DropdownMenu>
        <DropdownMenuTrigger asChild>
            <Button type="button" variant="ghost" size="sm" aria-label={label} title={label}>
                <span className="max-w-40 truncate">{items.find((item) => item.value === value)?.label ?? value}</span>
                <ChevronDownIcon />
            </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="max-h-72 overflow-y-auto">
            {items.map((item) => (
                <DropdownMenuItem key={item.value} onSelect={() => onPick(item.value)}>
                    <span className="flex-1">{item.label}</span>
                    {item.value === value && <CheckIcon />}
                </DropdownMenuItem>
            ))}
        </DropdownMenuContent>
    </DropdownMenu>
)

/** Model and effort pickers in the composer, limited to what the admin allows. Effort shows only for models that have it. */
export const ChatbotModelPicker = () => {
    const { options, choice, pickModel, pickEffort } = useChatbotChoice()
    if (!choice) return null
    const efforts = options.find((option) => option.model === choice.model)?.efforts ?? []

    return (
        <div className="flex items-center">
            <Picker label={_("Model")} value={choice.model} items={options.map(({ model }) => ({ value: model, label: model }))} onPick={pickModel} />
            {efforts.length > 0 && choice.effort && (
                <Picker label={_("Effort")} value={choice.effort} items={efforts.map((effort) => ({ value: effort, label: effortLabel(effort) }))} onPick={pickEffort} />
            )}
        </div>
    )
}
