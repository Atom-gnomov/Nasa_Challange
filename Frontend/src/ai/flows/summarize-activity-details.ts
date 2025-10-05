'use server';

/**
 * @fileOverview Summarizes activity details, including conditions, risks, and preparations.
 *
 * - summarizeActivityDetails - A function that summarizes activity details.
 * - SummarizeActivityDetailsInput - The input type for the summarizeActivityDetails function.
 * - SummarizeActivityDetailsOutput - The return type for the summarizeActivityDetails function.
 */

import {ai} from '@/ai/genkit';
import {z} from 'genkit';

const SummarizeActivityDetailsInputSchema = z.object({
  activityName: z.string().describe('The name of the activity.'),
  location: z.string().describe('The location of the activity.'),
  date: z.string().describe('The date of the activity (YYYY-MM-DD).'),
  parameters: z.record(z.string(), z.any()).describe('A map of parameter names to their values relevant to the activity.'),
});
export type SummarizeActivityDetailsInput = z.infer<typeof SummarizeActivityDetailsInputSchema>;

const SummarizeActivityDetailsOutputSchema = z.object({
  summary: z.string().describe('A summary of the activity details, including key conditions, potential risks, and necessary preparations.'),
});
export type SummarizeActivityDetailsOutput = z.infer<typeof SummarizeActivityDetailsOutputSchema>;

export async function summarizeActivityDetails(input: SummarizeActivityDetailsInput): Promise<SummarizeActivityDetailsOutput> {
  return summarizeActivityDetailsFlow(input);
}

const prompt = ai.definePrompt({
  name: 'summarizeActivityDetailsPrompt',
  input: {schema: SummarizeActivityDetailsInputSchema},
  output: {schema: SummarizeActivityDetailsOutputSchema},
  model: 'googleai/gemini-1.5-flash',
  prompt: `Summarize the key conditions, potential risks, and necessary preparations for the following activity:\n\nActivity: {{{activityName}}}\nLocation: {{{location}}}\nDate: {{{date}}}\nParameters: {{{parameters}}}\n\nFocus on providing a concise and informative summary that helps the user understand what to expect and how to best prepare.  The summary should be no more than 100 words.`,
});

const summarizeActivityDetailsFlow = ai.defineFlow(
  {
    name: 'summarizeActivityDetailsFlow',
    inputSchema: SummarizeActivityDetailsInputSchema,
    outputSchema: SummarizeActivityDetailsOutputSchema,
  },
  async input => {
    const {output} = await prompt(input);
    return output!;
  }
);
