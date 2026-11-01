import { DialogConfig } from '@angular/cdk/dialog';

/**
 * Accessible name and role for a CDK dialog. The CDK container is the element
 * with role="dialog", so it gets the title's id; the dialog's own markup must
 * not repeat the role (a screen reader would announce two nested dialogs).
 */
export function dialogA11y(
  titleId: string,
  options: { alert?: boolean; describedBy?: string } = {},
): Pick<DialogConfig, 'role' | 'ariaModal' | 'ariaLabelledBy' | 'ariaDescribedBy'> {
  return {
    role: options.alert ? 'alertdialog' : 'dialog',
    ariaModal: true,
    ariaLabelledBy: titleId,
    ariaDescribedBy: options.describedBy ?? null,
  };
}
