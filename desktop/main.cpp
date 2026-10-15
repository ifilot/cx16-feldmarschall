#include "desk.h"
#include <QApplication>
#include <QCommandLineParser>
#include <QDir>
#include <QFileInfo>
#include <QStandardPaths>
#include <QTimer>
#include <iostream>

int main(int argc, char **argv) {
    QApplication app(argc, argv); app.setStyle("Fusion");
    QCoreApplication::setApplicationName("feldmarschall-desk");
    QCommandLineParser parser; parser.setApplicationDescription("Native Qt6 Classic tournament desk"); parser.addHelpOption();
    parser.addOption({"project", "Project directory containing ai/registry.json", "path", FMT_PROJECT_ROOT});
    parser.addOption({"python", "Python interpreter for source builds and tournament storage", "program", QStandardPaths::findExecutable("python3")});
    parser.addOption({"smoke-test", "Run an offscreen integration tournament into a new file", "path"});
    parser.addOption({"screenshot", "Save the integration-test window", "path"});
    parser.addOption({"capture-review", "Capture an existing tournament and exit", "path"});
    parser.addOption({"match", "Match ID for review capture", "id", "1"});
    parser.addOption({"ply", "Ply for review capture", "ply", "0"});
    parser.addOption({"view", "Review perspective: 0 both, 1 Red, 2 Blue", "view", "0"});
    parser.addPositionalArgument("tournament", "Optional .fmtour file to review"); parser.process(app);
    try {
        auto root = QFileInfo(parser.value("project")).absoluteFilePath();
        QString worker = QCoreApplication::applicationDirPath() + "/feldmarschall-tournament-worker";
#ifdef Q_OS_WIN
        worker += ".exe";
#endif
        Desk desk(root, parser.value("python"), worker); desk.show();
        if (!parser.positionalArguments().isEmpty()) desk.openTournament(parser.positionalArguments().first());
        if (parser.isSet("capture-review")) {
            desk.openTournament(parser.value("capture-review"));
            desk.captureReview(parser.value("match").toInt(), parser.value("ply").toInt(), parser.value("view").toInt());
            QTimer::singleShot(200, &app, [&] { app.exit(desk.grab().save(parser.value("screenshot")) ? 0 : 1); });
        }
        if (parser.isSet("smoke-test")) {
            desk.finished = [&](bool ok) {
                try { ok = ok && desk.verifySmoke(); } catch (const std::exception &error) { std::cerr << error.what() << std::endl; ok = false; }
                if (ok && parser.isSet("screenshot")) ok = desk.grab().save(parser.value("screenshot"));
                std::cout << (ok ? "Native Qt6 tournament and review passed" : "Native Qt6 integration failed") << std::endl;
                app.exit(ok ? 0 : 1);
            };
            QTimer::singleShot(0, &desk, [&] { desk.startSmoke(parser.value("smoke-test")); });
            QTimer::singleShot(90000, &app, [&] { std::cerr << "Integration timeout" << std::endl; app.exit(1); });
        }
        return app.exec();
    } catch (const std::exception &error) { std::cerr << error.what() << std::endl; return 1; }
}
