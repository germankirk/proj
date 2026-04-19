try:
	# Ensure signals are registered when the app is imported (covers cases
	# where AppConfig.ready may not be invoked depending on INSTALLED_APPS).
	import main.signals  # noqa: F401
except Exception:
	# Avoid import-time errors blocking Django startup; errors will surface
	# when signal handlers actually run and can be diagnosed then.
	pass
