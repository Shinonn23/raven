import { useFieldArray, useFormContext } from "react-hook-form"
import { PlusIcon, Trash2Icon } from "lucide-react"
import { Button } from "@components/ui/button"
import { DataField, SmallTextField } from "@components/ui/form-elements"
import type { RavenSettings } from "@raven/types/Raven/RavenSettings"
import _ from "@lib/translate"

/** The manual sites the Chatbot can search and read, each with the API key of its read-only service user. */
export const ManualSourcesField = () => {
    const { control, formState } = useFormContext<RavenSettings>()
    const { fields, append, remove } = useFieldArray({ control, name: "manual_sources" })

    return (
        <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between gap-2">
                <div>
                    <div className="text-base-medium text-ink-gray-8">{_("Manual Sources")}</div>
                    <p className="text-p-sm text-ink-gray-5">{_("Manual sites the Chatbot searches and reads to answer how-to questions.")}</p>
                </div>
                <Button type="button" variant="outline" size="sm" disabled={formState.disabled}
                    onClick={() => append({ source_name: "", base_url: "https://", description: "", api_key: "", api_secret: "" } as never)}>
                    <PlusIcon />{_("Add")}
                </Button>
            </div>
            {fields.map((row, index) => (
                <div key={row.id} className="flex flex-col gap-3 rounded-lg border border-outline-gray-2 p-3">
                    <div className="grid gap-3 md:grid-cols-2">
                        <DataField name={`manual_sources.${index}.source_name`} label={_("Name")} isRequired
                            formDescription={_("A short name the AI uses to pick it, e.g. manual or uat.")}
                            rules={{ required: _("Name is required") }} inputProps={{ placeholder: "manual", autoComplete: "off" }} />
                        <DataField name={`manual_sources.${index}.base_url`} label={_("Site URL")} isRequired
                            rules={{ required: _("Site URL is required") }} inputProps={{ placeholder: "https://manual.connectdiagnostics.net", autoComplete: "off" }} />
                    </div>
                    <SmallTextField name={`manual_sources.${index}.description`} label={_("What it covers")} isRequired
                        formDescription={_("The AI reads this to decide when to search it.")}
                        rules={{ required: _("A description is required") }} />
                    <div className="grid gap-3 md:grid-cols-2">
                        <DataField name={`manual_sources.${index}.api_key`} label={_("API Key")} isRequired
                            rules={{ required: _("API Key is required") }} inputProps={{ autoComplete: "off" }} />
                        <DataField name={`manual_sources.${index}.api_secret`} label={_("API Secret")} isRequired
                            rules={{ required: _("API Secret is required") }} inputProps={{ type: "password", autoComplete: "off" }} />
                    </div>
                    <div className="flex justify-end">
                        <Button type="button" variant="ghost" theme="red" size="sm" disabled={formState.disabled} onClick={() => remove(index)}>
                            <Trash2Icon />{_("Remove")}
                        </Button>
                    </div>
                </div>
            ))}
        </div>
    )
}
