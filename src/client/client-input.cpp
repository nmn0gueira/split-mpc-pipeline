#include "Math/gfp.h"
#include "Math/gf2n.h"
#include "Networking/sockets.h"
#include "Networking/ssl_sockets.h"
#include "Tools/int.h"
#include "Math/Setup.h"
#include "Protocols/fake-stuff.h"

#include "Math/gfp.hpp"
#include "Client.hpp"

#include <sodium.h>
#include <iostream>
#include <sstream>
#include <fstream>


template<class T, class U>
void run(const std::vector<string> &strs, int output_length, Client& client)
{
    std::vector<T> values;
    values.reserve(strs.size());
    for (const auto& s : strs) {
        values.emplace_back(long(round(std::stoi(s))));    // sint
    }

    //one_run<T, U>(long(round(salary_value)), client);
    // sfix with f = 16
    //one_run<T, U>(long(round(salary_value * exp2(16))), client);

    // Run the computation
    client.send_private_inputs<T>(values);
    cout << "Sent private inputs to each SPDZ engine, waiting for result..." << endl;

    std::vector<U> result = client.receive_outputs<T>(output_length);

    // Get the result back (client_id of winning client)
    for (const auto& r : result)
        cout << "Output: " << r << endl;
}

std::vector<std::string> read_csv_column(const std::string& filename,
                                       std::size_t col_index)
{
    std::vector<std::string> column;
    std::ifstream file(filename);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open file: " + filename);
    }

    std::string line;
    while (std::getline(file, line)) {
        std::stringstream ss(line);
        std::string cell;
        std::size_t current = 0;

        // split the line on commas
        while (std::getline(ss, cell, ',')) {
            if (current == col_index) {
                column.push_back(cell);
                break;
            }
            ++current;
        }
    }

    return column;
}

int main(int argc, char** argv)
{
    int client_id;
    int nparties;
    std::string input_file;
    int output_length;
    size_t finish;
    int port_base;
    std::vector<std::string> hostnames;

    auto usage = [&]() -> int {
        std::cerr << "Usage: " << argv[0]
                  << " --client_id <client_identifier>"
                  << " --nparties <number_of_parties>"
                  << " --in <input_file>"
                  << "--out_len <output_elements_num>"
                  << " [--finish]"
                  << " [--port_base <port>]"
                  << " [--hosts <host_1,host_2,...,host_n>]"
                  << std::endl;
        return 1;
    };


    // Very simple arg parser
    std::unordered_map<std::string, std::string> args;
    for (int i = 1; i < argc; ++i) {
        std::string key = argv[i];

        if (key.rfind("--", 0) != 0) {
            std::cerr << "Unexpected positional argument: " << key << '\n';
            return usage();
        }

        bool has_next = (i + 1 < argc);
        bool next_is_flag = has_next && std::string(argv[i + 1]).rfind("-", 0) == 0;

        if (!has_next || next_is_flag) {    // store true
            args[key] = "1";
        } else {
            args[key] = argv[i + 1];
            ++i;
        }
    }

    try {
        client_id   = std::stoi(args.at("--client_id"));
        nparties    = std::stoi(args.at("--nparties"));
        input_file = args.at("--in");
        output_length = std::stoi(args.at("--out_len"));
        finish = args.count("--finish") ? std::stoi(args.at("--finish")) : 0;
        port_base = args.count("--port_base") ? std::stoi(args.at("--port_base")) : 14000;

        if (args.count("--hosts")) {
            std::istringstream ss(args.at("--hosts"));
            std::string host;
            while (std::getline(ss, host, ',')) {
                hostnames.push_back(host);
            }
        } else {
            hostnames.assign(nparties, "localhost");
        }

        std::cout << "client_id: " << client_id << "\n"
                  << "nparties: " << nparties << "\n"
                  << "input: " << input_file << "\n"
                  << "out_len: " << output_length << "\n"
                  << "finish: " << finish << "\n"
                  << "port_base: " << port_base << "\n"
                  << "hosts: ";
        for (const auto& h : hostnames) std::cout << h << ' ';
        std::cout << '\n';
    } catch (const std::out_of_range&) {
        std::cerr << "Missing required argument.\n";
        return usage();
    } catch (const std::invalid_argument&) {
        std::cerr << "Invalid numeric value.\n";
        return usage();
    }


    std::vector<std::string> strs = read_csv_column(input_file, finish);
    
    bigint::init_thread();

    // Setup connections from this client to each party socket
    Client client(hostnames, port_base, client_id);
    auto& specification = client.specification;
    auto& sockets = client.sockets;
    for (int i = 0; i < nparties; i++)
    {
        octetStream os;
        os.store(finish);
        os.Send(sockets[i]);
    }
    cout << "Finish setup socket connections to SPDZ engines." << endl;

    int type = specification.get<int>();
    switch (type)
    {
    case 'p':
    {
        gfp::init_field(specification.get<bigint>());
        cerr << "using prime " << gfp::pr() << endl;
        run<gfp, gfp>(strs, output_length, client);
        break;
    }
    case 'R':
    {
        int R = specification.get<int>();
        int R2 = specification.get<int>();
        if (R != R2)
        {
            cerr << "R (" << R << ") different than R2 (" << R2 << ")." << endl;
        }

        switch (R)
        {
        case 64:
            run<Z2<64>, Z2<64>>(strs, output_length, client);
            break;
        case 128:
            //run<Z2<128>, Z2<64>>(strs, client);   // This was the original, but it resulted in errors when assigning the output of client.receive_outputs to a vector<U>, apparently due to conversion errors from Z2<128> to Z2<64>
            run<Z2<128>, Z2<128>>(strs, output_length, client);
            break;
        default:
            cerr << R << "-bit ring not implemented";
            exit(1);
        }
        break;
    }
    default:
        cerr << "Type " << type << " not implemented";
        exit(1);
    }

    return 0;
}
