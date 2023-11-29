import { App, Editor, MarkdownView, Modal, Notice, Plugin, PluginSettingTab, Setting } from 'obsidian';

// Remember to rename these classes and interfaces!

interface MyPluginSettings {
	openaiApiKey: string;
}

const DEFAULT_SETTINGS: MyPluginSettings = {
	openaiApiKey: ''
}

export default class AthenaPlugin extends Plugin {
	settings: MyPluginSettings;

	async onload() {
		await this.loadSettings();

		// This creates an icon in the left ribbon.
		const ribbonIconEl = this.addRibbonIcon('dice', 'Athena', (evt: MouseEvent) => {
			// Called when the user clicks the icon.
			new Notice('This is a notice from Athena!');
		});

		// Perform additional things with the ribbon
		ribbonIconEl.addClass('my-plugin-ribbon-class');

		// This adds a status bar item to the bottom of the app. Does not work on mobile apps.
		const statusBarItemEl = this.addStatusBarItem();
		statusBarItemEl.setText('Athena Online');

		// This adds a simple command that can be triggered anywhere
		this.addCommand({
			id: 'open-athena-modal-simple',
			name: 'Open Athena modal (simple)',
			callback: () => {
				new SampleModal(this.app).open();
			}
		});

		// This adds an editor command that can perform some operation on the current editor instance
		this.addCommand({
			id: 'athena-editor-command',
			name: 'Athena simple editor command',
			editorCallback: (editor: Editor, view: MarkdownView) => {
				console.log(editor.getSelection());
				editor.replaceSelection('Athena Editor Command');
			}
		});

		// This adds a complex command that can check whether the current state of the app allows execution of the command
		this.addCommand({
			id: 'open-athena-modal-complex',
			name: 'Open Athena modal (complex)',
			checkCallback: (checking: boolean) => {
				// Conditions to check
				const markdownView = this.app.workspace.getActiveViewOfType(MarkdownView);
				if (markdownView) {
					// If checking is true, we're simply "checking" if the command can be run.
					// If checking is false, then we want to actually perform the operation.
					if (!checking) {
						new SampleModal(this.app).open();
					}

					// This command will only show up in Command Palette when the check function returns true
					return true;
				}
			}
		});

		// This adds a settings tab so the user can configure various aspects of the plugin
		this.addSettingTab(new SampleSettingTab(this.app, this));

		// If the plugin hooks up any global DOM events (on parts of the app that doesn't belong to this plugin)
		// Using this function will automatically remove the event listener when this plugin is disabled.
		// this.registerDomEvent(document, 'click', (evt: MouseEvent) => {
		// 	console.log('click', evt);
		// });

		// When registering intervals, this function will automatically clear the interval when the plugin is disabled.
		// this.registerInterval(window.setInterval(() => console.log('setInterval'), 5 * 60 * 1000));
	}

	onunload() {

	}

	async loadSettings() {
		this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
	}

	async saveSettings() {
		await this.saveData(this.settings);
		await this.saveApiKeyToFile(this.settings.openaiApiKey);
	}

	async saveApiKeyToFile(apiKey: string) {
        const fileContent = `OPENAI_API_KEY=${apiKey}\n`;
        const filePath = this.app.vault.adapter.basePath + '/python/.env';
        await this.app.vault.adapter.write(filePath, fileContent);
    }
}

class SampleModal extends Modal {
	constructor(app: App) {
		super(app);
	}

	onOpen() {
		const {contentEl} = this;
		contentEl.setText('Woah!');
	}

	onClose() {
		const {contentEl} = this;
		contentEl.empty();
	}
}

class SampleSettingTab extends PluginSettingTab {
	plugin: AthenaPlugin;

	constructor(app: App, plugin: AthenaPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const {containerEl} = this;

		containerEl.empty();

		new Setting(containerEl)
			.setName('OpenAI API Key')
			.setDesc('This is necessary for functioning of the plugin')
			.addText(text => text
				.setPlaceholder('OpenAI API Key')
				.setValue(this.plugin.settings.openaiApiKey)
				.onChange(async (value) => {
					this.plugin.settings.openaiApiKey = value;
					await this.plugin.saveSettings();
				}));
	}
}
